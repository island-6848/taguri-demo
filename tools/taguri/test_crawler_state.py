"""取得処理の作業データを、実行の間で引き継ぐ流れの検査（S3 は偽物）。

    python3 tools/taguri/test_crawler_state.py
"""
from __future__ import annotations

import io
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import crawler_state as CS                                           # noqa: E402


class FakeS3:
    def __init__(self):
        self.objects: dict[str, bytes] = {}

    def head_object(self, Bucket, Key):
        if Key not in self.objects:
            raise KeyError(Key)
        return {}

    def download_file(self, Bucket, Key, Filename):
        Path(Filename).write_bytes(self.objects[Key])

    def upload_file(self, Filename, Bucket, Key):
        self.objects[Key] = Path(Filename).read_bytes()


def tar_bytes(files: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for name, text in files.items():
            data = text.encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
    return buf.getvalue()


class CrawlerState(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name) / "data"
        self.p = patch.object(CS, "DATA", self.data)
        self.p.start()
        self.s3 = FakeS3()

    def tearDown(self):
        self.p.stop()
        self.tmp.cleanup()

    def test_first_run_seeds_from_the_public_catalog(self):
        self.s3.objects[CS.S3_KEY] = tar_bytes({"review/candidates.jsonl": "{}"})
        self.assertEqual(CS.restore(self.s3), "catalog")
        self.assertTrue((self.data / "review" / "candidates.jsonl").exists())

    def test_save_then_restore_keeps_caches_but_not_records(self):
        (self.data / "review").mkdir(parents=True)
        (self.data / "auth").mkdir()
        (self.data / "review" / "candidates.jsonl").write_text("{}")
        (self.data / "review" / "requests_cache.json").write_text("{}")
        (self.data / "review" / "ratings.db").write_text("secret")
        (self.data / "auth" / "auth.db").write_text("secret")
        (self.data / "review" / "x.part").write_text("tmp")
        self.assertEqual(CS.save(self.s3), 2)
        self.s3.objects[CS.S3_KEY] = tar_bytes({"review/candidates.jsonl": "old"})
        for p in sorted(self.data.rglob("*"), reverse=True):
            p.unlink() if p.is_file() else p.rmdir()
        self.assertEqual(CS.restore(self.s3), "state")                # 作業データを優先する
        names = sorted(p.relative_to(self.data).as_posix() for p in self.data.rglob("*") if p.is_file())
        self.assertEqual(names, ["review/candidates.jsonl", "review/requests_cache.json"])
        self.assertEqual((self.data / "review" / "candidates.jsonl").read_text(), "{}")

    def test_unsafe_archives_are_refused(self):
        for bad in ("../evil", "/abs"):
            self.s3.objects[CS.STATE_KEY] = tar_bytes({bad: "x"})
            with self.assertRaises(ValueError):
                CS.restore(self.s3)

    def test_empty_when_nothing_exists(self):
        self.assertEqual(CS.restore(self.s3), "empty")


if __name__ == "__main__":
    unittest.main()
