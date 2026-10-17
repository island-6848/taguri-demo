"""取得処理の作業データを、実行の間で引き継ぐ流れの検査。

    python3 tools/taguri/test_crawler_state.py
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import crawler_state as CS                                           # noqa: E402


class CrawlerState(unittest.TestCase):
    def setUp(self):
        CS._UPLOADED = None
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.data = base / "data"
        self.state = base / "state"
        self.p = patch.object(CS, "DATA", self.data)
        self.p.start()

    def tearDown(self):
        self.p.stop()
        self.tmp.cleanup()

    def files(self, base):
        return sorted(p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file())

    def test_first_run_starts_empty(self):
        self.assertEqual(CS.restore(self.state), 0)

    def test_save_then_restore_keeps_caches_but_not_records(self):
        (self.data / "review").mkdir(parents=True)
        (self.data / "auth").mkdir()
        (self.data / "review" / "candidates.jsonl").write_text("{}")
        (self.data / "review" / "requests_cache.json").write_text("{}")
        (self.data / "review" / "ratings.db").write_text("secret")
        (self.data / "auth" / "auth.db").write_text("secret")
        (self.data / "review" / "x.part").write_text("tmp")
        (self.state / ".git").mkdir(parents=True)
        (self.state / ".git" / "HEAD").write_text("ref")
        (self.state / "review").mkdir()
        (self.state / "review" / "gone.jsonl").write_text("old")      # 前回の古い控え
        self.assertEqual(CS.save(self.state), 2)
        self.assertEqual(self.files(self.state), [".git/HEAD", "review/candidates.jsonl", "review/requests_cache.json"])
        fresh = Path(self.tmp.name) / "fresh"
        with patch.object(CS, "DATA", fresh):
            self.assertEqual(CS.restore(self.state), 2)
            self.assertEqual(self.files(fresh), ["review/candidates.jsonl", "review/requests_cache.json"])

    def test_backups_of_user_records_are_never_kept(self):
        # 安全の点検 2026-10-17: 控えの平文が state ブランチ（git）に残らない
        for name in ("backup.sql", "drill.sql", "d1/x.sql.gpg"):
            self.assertFalse(CS.keep(name), name)
        self.assertTrue(CS.keep("d1/delivered.json"))

    def test_posters_already_in_r2_are_left_out(self):
        img = self.data / "review" / "img"
        img.mkdir(parents=True)
        for n in ("1.jpg", "2.jpg"):
            (img / n).write_bytes(b"x")
        (self.data / "r2").mkdir()
        (self.data / "r2" / "posters.json").write_text('{"1": "1.jpg"}')
        CS.save(self.state)
        self.assertEqual(self.files(self.state), ["r2/posters.json", "review/img/2.jpg"])

    def test_links_are_not_followed(self):
        (self.state / "review").mkdir(parents=True)
        secret = Path(self.tmp.name) / "secret.txt"
        secret.write_text("x")
        (self.state / "review" / "link.json").symlink_to(secret)
        self.assertEqual(CS.restore(self.state), 0)


if __name__ == "__main__":
    unittest.main()
