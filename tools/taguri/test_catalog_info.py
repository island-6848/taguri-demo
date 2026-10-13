"""カタログの日付を残し、公開の /api/health で返し、古ければ知らせる流れの検査。

    python3 tools/taguri/test_catalog_info.py
"""
from __future__ import annotations

import datetime
import io
import json
import os
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
sys.path.insert(0, str(ROOT / "tools" / "taguri"))
import catalog_info as CI                                            # noqa: E402
import check_catalog_age as CHK                                      # noqa: E402

TODAY = datetime.date(2026, 10, 13)


def make_archive(path: Path, files: dict[str, tuple[str, float]]) -> None:
    with tarfile.open(path, "w:gz") as tf:
        for name, (text, mtime) in files.items():
            data = text.encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mtime = mtime
            tf.addfile(info, io.BytesIO(data))


def ts(day: str) -> float:
    return datetime.datetime.fromisoformat(day + "T03:00:00+00:00").timestamp()


class CatalogInfo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        CI.clear_cache()

    def tearDown(self):
        CI.clear_cache()
        self.tmp.cleanup()

    def test_archive_newest_file_and_upcoming_counts(self):
        rows = [{"period": "2026/10/01〜2026/10/20"}, {"period": "2026/09/01 - 2026/09/30"},
                {"period": "読めない"}, {"period": "2026/12/01〜2026/12/05"}]
        archive = self.root / "c.tar.gz"
        make_archive(archive, {
            "review/candidates.jsonl": ("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), ts("2026-08-30")),
            "review/candidates_scan.json": (json.dumps({"date": "2026-08-29"}), ts("2026-08-29")),
        })
        info = CI.archive_info(archive)
        self.assertEqual(info["newest_file"][:10], "2026-08-30")
        self.assertEqual(info["files"], 2)
        data = self.root / "data"
        with tarfile.open(archive) as tf:
            tf.extractall(data, filter="data")
        CI.write_info(data, {**info, "uploaded_at": "2026-08-30T04:00:00+00:00"})
        got = CI.describe(data, TODAY)
        self.assertTrue(got["present"])
        self.assertEqual(got["scan_date"], "2026-08-29")
        self.assertEqual(got["upcoming"]["candidates"], 2)          # 10/20 と 12/05
        self.assertEqual(got["age_days"], (TODAY - datetime.date(2026, 8, 30)).days)
        blob = json.dumps(got, ensure_ascii=False)
        self.assertNotIn("period", blob)                            # 中身は出さない

    def test_missing_catalog_is_reported_not_raised(self):
        self.assertEqual(CI.describe(self.root / "none", TODAY), {"present": False, "upcoming": {}})

    def test_install_records_dates(self):
        import serve_cloud as SC
        archive = self.root / "c.tar.gz"
        make_archive(archive, {"review/candidates.jsonl": ('{"period": "2026/11/01"}', ts("2026-10-12"))})
        with patch.object(SC, "ROOT", self.root):
            SC._install_catalog(archive, "2026-10-12T04:30:00+00:00")
        info = json.loads((self.root / "data" / CI.INFO_NAME).read_text())
        self.assertEqual(info["uploaded_at"], "2026-10-12T04:30:00+00:00")
        self.assertEqual(info["newest_file"][:10], "2026-10-12")

    def test_health_returns_catalog_dates(self):
        import test_demo_stability as DS

        class T(unittest.TestCase):
            setUpClass = classmethod(DS.DemoStabilityTests.setUpClass.__func__)
            tearDownClass = classmethod(DS.DemoStabilityTests.tearDownClass.__func__)
            request = DS.DemoStabilityTests.request

            def test(inner):
                status, body = inner.request("/api/health", extra={"Cookie": ""})
                inner.assertEqual(status, 200)
                inner.assertIn("catalog", body)
                inner.assertIn("present", body["catalog"])
        r = unittest.TextTestRunner(stream=io.StringIO()).run(unittest.defaultTestLoader.loadTestsFromTestCase(T))
        self.assertTrue(r.wasSuccessful(), r.failures + r.errors)


class Checker(unittest.TestCase):
    def test_judge(self):
        fresh = {"present": True, "uploaded_at": "2026-10-12T04:00:00+00:00", "upcoming": {"candidates": 500}}
        self.assertEqual(CHK.judge(fresh, TODAY, 3, 100), [])
        old = {"present": True, "newest_file": "2026-08-30T03:00:00+00:00", "upcoming": {"candidates": 500}}
        self.assertTrue(any("古い" in p for p in CHK.judge(old, TODAY, 3, 100)))
        few = {**fresh, "upcoming": {"candidates": 3}}
        self.assertTrue(any("少ない" in p for p in CHK.judge(few, TODAY, 3, 100)))
        self.assertTrue(CHK.judge({"present": True, "upcoming": {"candidates": 500}}, TODAY, 3, 100))
        self.assertTrue(CHK.judge({}, TODAY, 3, 100))

    def test_main_exit_codes(self):
        class Res(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        body = {"ok": True, "catalog": {"present": True, "uploaded_at": datetime.date.today().isoformat(),
                                        "upcoming": {"candidates": 500}}}
        with patch.object(CHK.urllib.request, "urlopen", return_value=Res(json.dumps(body).encode())), \
             patch.object(sys, "argv", ["x"]), patch("sys.stdout", io.StringIO()):
            self.assertEqual(CHK.main(), 0)
        body["catalog"]["uploaded_at"] = "2026-01-01"
        with patch.object(CHK.urllib.request, "urlopen", return_value=Res(json.dumps(body).encode())), \
             patch.object(sys, "argv", ["x"]), patch("sys.stdout", io.StringIO()):
            self.assertEqual(CHK.main(), 1)
        with patch.object(CHK.urllib.request, "urlopen", side_effect=CHK.urllib.error.URLError("down")), \
             patch.object(CHK.time, "sleep"), patch.object(sys, "argv", ["x"]), patch("sys.stdout", io.StringIO()):
            self.assertEqual(CHK.main(), 2)


if __name__ == "__main__":
    unittest.main()
