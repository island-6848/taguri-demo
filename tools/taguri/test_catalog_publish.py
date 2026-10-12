#!/usr/bin/env python3
"""カタログの作り直し（publish_catalog.py）と、サーバー側の入れ替え（serve_cloud._refresh_loop）の検査。

外部にも S3 にも通信しない（boto3 は偽物に差し替える）。

    python3 tools/taguri/test_catalog_publish.py
"""
from __future__ import annotations

import json
import os
import sys
import tarfile
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "taguri"))
import publish_catalog as PC                                        # noqa: E402


def make_data(d: Path, n_upcoming: int = 150) -> None:
    (d / "review").mkdir(parents=True)
    (d / "credits").mkdir()
    (d / "auth").mkdir()
    (d / "tickets").mkdir()
    with (d / "review" / "candidates.jsonl").open("w", encoding="utf-8") as f:
        for i in range(n_upcoming):
            f.write(json.dumps({"stage_id": str(i), "period": "2026/10/20〜2026/11/30"}) + "\n")
        f.write(json.dumps({"stage_id": "old", "period": "2026/01/01〜2026/01/02"}) + "\n")
    (d / "review" / "recommend2.json").write_text("{}")
    (d / "credits" / "themes.jsonl").write_text("")
    for p in ("auth/auth.db", "auth/auth_pepper.txt", "review/ratings.db", "review/ratings.db-wal",
              "tickets/performances.jsonl", "review/lookback.json", "review/chronicle.json",
              "review/people_read.json", "review/declared.json", "review/declined.json",
              "credits/official_fail.json", "review/x.part", ".hidden"):
        (d / p).write_text("secret")
    os.symlink("/etc/hostname", d / "review" / "link.txt")


class Publish(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name) / "data"
        make_data(self.data)
        self._old = PC.DATA
        PC.DATA = self.data

    def tearDown(self):
        PC.DATA = self._old
        self.tmp.cleanup()

    def test_only_public_files_are_packed(self):
        arc = Path(self.tmp.name) / "c.tar.gz"
        PC.build(arc)
        PC.verify(arc)
        with tarfile.open(arc) as tf:
            names = sorted(tf.getnames())
        self.assertEqual(names, ["credits/themes.jsonl", "review/candidates.jsonl", "review/recommend2.json"])

    def test_verify_rejects_private_files(self):
        arc = Path(self.tmp.name) / "bad.tar.gz"
        with tarfile.open(arc, "w:gz") as tf:
            tf.add(self.data / "review" / "candidates.jsonl", arcname="review/candidates.jsonl")
            tf.add(self.data / "review" / "ratings.db", arcname="review/ratings.db")
        with self.assertRaises(SystemExit):
            PC.verify(arc)

    def test_counts_only_upcoming(self):
        self.assertEqual(PC.count_upcoming("2026-10-12")["candidates"], 150)

    def test_refuses_when_too_few(self):
        (self.data / "review" / "candidates.jsonl").write_text(
            json.dumps({"stage_id": "1", "period": "2026/10/20〜2026/11/30"}) + "\n")
        argv = ["publish_catalog.py", "--no-update", "--dry-run", "--today", "2026-10-12",
                "--data-dir", str(self.data)]
        with mock.patch.object(sys, "argv", argv):
            self.assertEqual(PC.main(), 1)

    def test_refuses_big_drop_from_previous(self):
        fake = mock.MagicMock()
        body = mock.MagicMock()
        body.read.return_value = json.dumps({"upcoming": {"candidates": 1000}}).encode()
        fake.get_object.return_value = {"Body": body}
        boto3 = types.SimpleNamespace(client=lambda *a, **k: fake)
        argv = ["publish_catalog.py", "--no-update", "--today", "2026-10-12", "--data-dir", str(self.data)]
        with mock.patch.dict(sys.modules, {"boto3": boto3}), mock.patch.object(sys, "argv", argv):
            self.assertEqual(PC.main(), 1)
        fake.upload_file.assert_not_called()

    def test_uploads_with_history_and_manifest(self):
        fake = mock.MagicMock()
        fake.get_object.side_effect = Exception("no manifest yet")
        fake.list_objects_v2.return_value = {"Contents": [{"Key": f"stage-catalog/history/data-{i:02d}.tar.gz"}
                                                          for i in range(10)]}
        boto3 = types.SimpleNamespace(client=lambda *a, **k: fake)
        argv = ["publish_catalog.py", "--no-update", "--today", "2026-10-12", "--data-dir", str(self.data)]
        with mock.patch.dict(sys.modules, {"boto3": boto3}), mock.patch.object(sys, "argv", argv):
            self.assertEqual(PC.main(), 0)
        fake.copy_object.assert_called_once()                      # 前のカタログを控える
        fake.upload_file.assert_called_once()
        manifest = json.loads(fake.put_object.call_args.kwargs["Body"])
        self.assertEqual(manifest["upcoming"]["candidates"], 150)
        self.assertEqual(len(manifest["sha256"]), 64)
        deleted = [c.kwargs["Key"] for c in fake.delete_object.call_args_list]
        self.assertEqual(deleted, ["stage-catalog/history/data-01.tar.gz",
                                   "stage-catalog/history/data-00.tar.gz"])   # 新しい 8 個だけ残す


class Refresh(unittest.TestCase):
    """動いているサーバーが、新しいカタログに入れ替えるかどうか。"""

    def _run(self, *, state_dir, etags):
        sys.modules.setdefault("boto3", types.SimpleNamespace(client=lambda *a, **k: None))
        import serve_cloud as SC
        srv = types.SimpleNamespace(screen_cache={"u|k": 1})
        calls = {"fetch": 0, "reset": 0}
        seq = iter(etags)

        def fake_sleep(_):
            try:
                SC._next_etag = next(seq)
            except StopIteration:
                raise KeyboardInterrupt from None

        fake_s3 = object()
        with mock.patch.object(SC.time, "sleep", fake_sleep), \
             mock.patch.object(SC.STATE, "state_dir", lambda: state_dir), \
             mock.patch.object(SC, "_remote_etag", lambda s3: SC._next_etag), \
             mock.patch.object(SC, "_fetch_catalog",
                               lambda: (calls.__setitem__("fetch", calls["fetch"] + 1),
                                        SC._installed_etag.__setitem__(0, SC._next_etag))), \
             mock.patch.object(SC.S.APP, "reset_caches",
                               lambda: calls.__setitem__("reset", calls["reset"] + 1)), \
             mock.patch.dict(sys.modules, {"boto3": types.SimpleNamespace(client=lambda *a, **k: fake_s3)}):
            SC._installed_etag[0] = '"A"'
            with self.assertRaises(KeyboardInterrupt):
                SC._refresh_loop(srv)
        return calls, srv

    def test_swaps_when_etag_changes(self):
        calls, srv = self._run(state_dir=Path("/var/data/taguri"), etags=['"A"', '"B"', '"B"'])
        self.assertEqual(calls, {"fetch": 1, "reset": 1})
        self.assertEqual(srv.screen_cache, {})

    def test_never_swaps_when_user_db_lives_in_data(self):
        calls, _ = self._run(state_dir=None, etags=['"B"', '"C"'])
        self.assertEqual(calls, {"fetch": 0, "reset": 0})


if __name__ == "__main__":
    unittest.main()
