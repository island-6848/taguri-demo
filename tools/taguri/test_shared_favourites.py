"""他の利用者のお気に入りの登録名でも、公演を探しに行けることの検査。

一時 DB と、実際の HTTP の解釈・振り分けを通す（外部への通信はしない）。
    python3 tools/taguri/test_shared_favourites.py
"""
from __future__ import annotations

import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_demo_stability as DS                                     # noqa: E402
APP = DS.APP
import favourites as FV                                              # noqa: E402

PATH = "/api/catalog/favourite-names"


class SharedNames(unittest.TestCase):
    # 一時 DB・仮のサーバー・利用者 2 人の用意は既存の検査から借りる（検査そのものは借りない）
    setUpClass = classmethod(DS.DemoStabilityTests.setUpClass.__func__)
    tearDownClass = classmethod(DS.DemoStabilityTests.tearDownClass.__func__)
    request = DS.DemoStabilityTests.request

    def setUp(self):
        APP.save_declared(self.users[0][0], {
            "人": ["俳優甲", "俳優乙", "https://example.com/x", "甲"], "題材": ["家族"]})
        APP.save_declared(self.users[1][0], {"人": ["俳優甲"], "団体": ["劇団乙"]})

    def test_names_are_merged_without_user_ids(self):
        names = APP.aggregate_declared_names()
        self.assertEqual(names[0], {"kind": "人", "name": "俳優甲", "users": 2})
        self.assertEqual({(n["kind"], n["name"]) for n in names},
                         {("人", "俳優甲"), ("人", "俳優乙"), ("団体", "劇団乙")})
        blob = json.dumps(names, ensure_ascii=False)
        for uid, _ in self.users:
            self.assertNotIn(uid, blob)

    def test_endpoint_is_absent_without_token(self):
        with patch.dict(os.environ, {"TAGURI_NAMES_TOKEN": ""}):
            status, _ = self.request(PATH)
        self.assertEqual(status, 404)

    def test_endpoint_requires_the_token(self):
        with patch.dict(os.environ, {"TAGURI_NAMES_TOKEN": "s3cret-token"}):
            self.assertEqual(self.request(PATH)[0], 403)
            self.assertEqual(self.request(PATH, extra={"Authorization": "Bearer wrong"})[0], 403)
            status, body = self.request(PATH, extra={"Authorization": "Bearer s3cret-token"})
        self.assertEqual(status, 200)
        self.assertEqual(body["version"], "favourite-names-v1")
        self.assertIn({"kind": "人", "name": "俳優甲", "users": 2}, body["names"])

    def test_fetcher_reads_names_and_rotates_by_cache_age(self):
        payload = {"names": [{"kind": "人", "name": "俳優甲", "users": 2},
                             {"kind": "題材", "name": "家族", "users": 1},
                             {"kind": "団体", "name": "劇団乙", "users": 1}]}

        class Res(io.BytesIO):
            def __enter__(self):
                return self
            def __exit__(self, *a):
                return False

        seen = {}

        def fake_urlopen(req, timeout=0):
            seen["auth"] = req.get_header("Authorization")
            return Res(json.dumps(payload).encode())

        with patch.object(FV, "NAMES_URL", "https://example.invalid" + PATH), \
             patch.object(FV, "NAMES_TOKEN", "t"), \
             patch.object(FV.urllib.request, "urlopen", fake_urlopen):
            got = FV.shared_names()
        self.assertEqual(seen["auth"], "Bearer t")
        self.assertEqual(got, [("人", "俳優甲"), ("団体", "劇団乙")])     # 題材は検索に回さない
        cache = {"人|俳優甲": {"at": "2026-10-10T04:00:00"}}
        self.assertEqual(FV.stale_first(got, cache), [("団体", "劇団乙"), ("人", "俳優甲")])

    def test_fetcher_continues_when_server_is_unreachable(self):
        with patch.object(FV, "NAMES_URL", "https://example.invalid" + PATH), \
             patch.object(FV, "NAMES_TOKEN", "t"), \
             patch.object(FV.urllib.request, "urlopen", side_effect=OSError("down")):
            self.assertEqual(FV.shared_names(), [])
        with patch.object(FV, "NAMES_URL", ""):
            self.assertEqual(FV.shared_names(), [])


if __name__ == "__main__":
    unittest.main()
