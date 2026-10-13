"""デモ版とサービス版の切り分けの検査（docs/editions.md）。

一時 DB と、実際の HTTP の解釈・振り分けを通す（外部への通信はしない）。
    python3 tools/taguri/test_editions.py
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_demo_stability as DS                                     # noqa: E402

APP, R = DS.APP, DS.R
NO_COOKIE = {"Cookie": ""}


def works_of(uid):
    with R.connect() as con:
        return R.read_works(con, user_id=uid)


class Demo(unittest.TestCase):
    setUpClass = classmethod(DS.DemoStabilityTests.setUpClass.__func__)
    tearDownClass = classmethod(DS.DemoStabilityTests.tearDownClass.__func__)
    request = DS.DemoStabilityTests.request

    def test_new_visitor_gets_the_samples_and_demo_flags(self):
        status, body = self.request("/api/health", extra=NO_COOKIE)
        self.assertEqual(status, 200)
        self.assertEqual((body["edition"], body["public"], body["demo_mode"]), ("demo", True, True))
        with patch.object(APP, "seed_demo_works", wraps=APP.seed_demo_works) as seed:
            status, body = self.request("/api/search_request", body={"q": "るつぼ"}, extra=NO_COOKIE)
        seed.assert_called_once()
        self.assertTrue(body.get("welcome_code"))

    def test_demo_input_never_reaches_the_fetchers(self):
        uid = self.users[0][0]
        status, body = self.request("/api/search_request", body={"q": "るつぼ"})
        self.assertEqual(status, 400)
        self.assertIn("デモ", body["error"])
        self.assertEqual(self.request("/api/missed", body={"title": "デモで見逃した芝居"})[0], 200)
        self.assertFalse(APP.has_search_request(uid, "デモで見逃した芝居"))
        self.assertNotIn("data-search-request", APP._web_hits(uid, "るつぼ", False))
        with patch.dict(os.environ, {"TAGURI_NAMES_TOKEN": "tok"}):
            for path in ("/api/catalog/favourite-names", "/api/catalog/search-requests"):
                status, _ = self.request(path, extra={"Authorization": "Bearer tok"})
                self.assertEqual(status, 404, path)


class Service(unittest.TestCase):
    setUpClass = classmethod(DS.service_setup)
    tearDownClass = classmethod(DS.service_teardown)
    request = DS.DemoStabilityTests.request

    def test_new_user_starts_empty_without_demo_wording(self):
        status, body = self.request("/api/health", extra=NO_COOKIE)
        self.assertEqual((body["edition"], body["public"], body["demo_mode"]), ("service", True, False))
        status, body = self.request("/api/search_request", body={"q": "サービスの題名"}, extra=NO_COOKIE)
        self.assertEqual(status, 200, body)
        self.assertTrue(body.get("welcome_code"))
        import auth as AU
        uid = AU.derive_user_id(body["welcome_code"])
        self.assertEqual(works_of(uid), {})                    # 見本は入らない
        self.assertEqual(APP.seed_demo_works(uid), 0)
        self.assertEqual(APP.link_demo_seed(uid), 0)
        self.assertNotIn("デモ", APP._web_hits(uid, "るつぼ", False))

    def test_public_restrictions_still_apply(self):
        # サービス版も公開運用なので、共有の公演情報は編集させず、その場で外部も検索しない
        for op in ("hand_theme", "hand_poster"):
            status, body = self.request("/api/" + op, body={"stage_id": "1", "work_key": "k"})
            self.assertEqual(status, 403, op)
            self.assertNotIn("デモ", body["error"])
        with patch.object(self.srv, "enqueue") as enqueue:
            self.assertEqual(self.request("/api/missed", body={"title": "見逃した芝居"})[0], 200)
        enqueue.assert_not_called()
        self.assertTrue(APP.has_search_request(self.users[0][0], "見逃した芝居"))


class CloudEntry(unittest.TestCase):
    def test_edition_must_be_known_and_service_needs_persistent_storage(self):
        import serve_cloud as SC
        with patch.dict(os.environ, {"TAGURI_EDITION": ""}):
            self.assertEqual(SC.edition(), "demo")
        with patch.dict(os.environ, {"TAGURI_EDITION": "Service"}):
            self.assertEqual(SC.edition(), "service")
        with patch.dict(os.environ, {"TAGURI_EDITION": "prod"}):
            with self.assertRaises(RuntimeError):
                SC.edition()
        with patch.object(SC.STATE, "state_dir", return_value=None):
            with self.assertRaises(RuntimeError):
                SC.check_service_storage("service")
            SC.check_service_storage("demo")                    # デモは一時保存でよい
        with patch.object(SC.STATE, "state_dir", return_value=Path("/var/taguri")), patch.object(SC.STATE, "exposure_path", return_value=Path("/var/taguri/recommendation_exposure.db")), patch.dict(os.environ, {"TAGURI_ALLOW_LOCAL_SERVICE": "1", "RENDER": "", "RENDER_SERVICE_ID": ""}):
            SC.check_service_storage("service")

    def test_server_rejects_unknown_edition_and_keeps_old_flag(self):
        import serve as S
        with patch("http.server.ThreadingHTTPServer.__init__", return_value=None):
            with self.assertRaises(ValueError):
                S.Server("x", 0, public=True, edition="prod")
        self.assertEqual(APP.EDITION in APP.EDITIONS, True)


if __name__ == "__main__":
    unittest.main()

