"""backup_d1.py: 利用者の記録の控え（S31）。D1・R2 には触れず、書き出しと置き場所を差し替えて確かめる。"""
import datetime as dt
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import backup_d1 as B  # noqa: E402
import free_tier as FT  # noqa: E402

MIGRATIONS = sorted((Path(__file__).resolve().parents[1] / "migrations").glob("*.sql"))
NOW = dt.datetime(2026, 10, 14, 20, 0, tzinfo=dt.timezone.utc)


def schema_tables() -> list[str]:
    con = sqlite3.connect(":memory:")
    for f in MIGRATIONS:
        con.executescript(f.read_text(encoding="utf-8"))
    names = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    con.close()
    return names


SQL = """CREATE TABLE users (id TEXT PRIMARY KEY, recovery_hash TEXT NOT NULL UNIQUE, created_at INTEGER NOT NULL);
INSERT INTO users VALUES('u1','h1',1),('u2','h2',2);
CREATE TABLE works (user_id TEXT, id TEXT);
INSERT INTO works VALUES('u1','w1');"""


class BackupTest(unittest.TestCase):
    def setUp(self):
        self.data = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.data)
        os.environ.update(CLOUDFLARE_ACCOUNT_ID="acc", CLOUDFLARE_API_TOKEN="tok", BACKUP_PASSPHRASE="correct horse")
        self.addCleanup(lambda: [os.environ.pop(k, None) for k in ("CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_API_TOKEN", "BACKUP_PASSPHRASE")])
        self.store = {}

    def run_backup(self, now=NOW, want=None, sql=SQL):
        export = lambda: (["users", "works"], want or {"users": 2, "works": 1}, sql)
        return B.backup(self.data, export=export, now=now,
                        put=lambda a, t, k, body: self.store.__setitem__(k, body),
                        delete=lambda a, t, k: self.store.pop(k))

    def test_every_user_table_is_backed_up_and_rebuildable_ones_are_not(self):
        got = B.user_tables(schema_tables())
        for t in ("users", "passkeys", "works", "favourites", "reaction", "ticket", "visit_note", "records", "reactions"):
            self.assertIn(t, got)
        for t in ("catalogue", "rec_stage", "rec_credit", "rec_cache", "past_stage", "poster", "usage", "sessions", "webauthn_challenges"):
            self.assertNotIn(t, got)
        self.assertEqual(B.user_tables(["works", "_cf_KV", "_cf_FOO", "sqlite_sequence"]), ["works"])

    @unittest.skipUnless(shutil.which("gpg"), "gpg が無い")
    def test_backup_is_encrypted_and_opens_with_the_passphrase(self):
        got = self.run_backup()
        key = "backup/d1/2026-10-14.sql.gpg"
        self.assertEqual((got["key"], got["rows"], got["tables"]), (key, 3, 2))
        body = self.store[key]
        self.assertNotIn(b"recovery_hash", body)
        self.assertEqual(B.decrypt(body, "correct horse").decode(), SQL)
        with self.assertRaises(RuntimeError):
            B.decrypt(body, "wrong")
        u = FT.load(self.data)
        self.assertEqual(u["r2"]["sizes"][key], len(body))
        self.assertEqual(FT.r2_class_a(u, NOW), 1)

    @unittest.skipUnless(shutil.which("gpg"), "gpg が無い")
    def test_a_backup_missing_rows_is_not_stored(self):
        with self.assertRaisesRegex(RuntimeError, "users: D1 3 行・控え 2 行"):
            self.run_backup(want={"users": 3, "works": 1})
        self.assertEqual(self.store, {})

    @unittest.skipUnless(shutil.which("gpg"), "gpg が無い")
    def test_thirty_days_are_kept_and_older_ones_removed(self):
        for i in range(35):
            self.run_backup(now=NOW - dt.timedelta(days=34 - i))
        keys = sorted(self.store)
        self.assertEqual(len(keys), 31)
        self.assertEqual(keys[0], "backup/d1/2026-09-14.sql.gpg")
        self.assertEqual(B.backup_keys(FT.load(self.data)), keys)

    def test_drill_reports_when_no_recent_backup_exists(self):
        import urllib.error

        def missing(a, t, k):
            raise urllib.error.HTTPError(k, 404, "not found", {}, None)
        got = B.drill(self.data, get=missing)
        self.assertEqual((got["ok"], got["mismatch"]), (False, ["この 4 日の控えが R2 に無い"]))

    def test_no_passphrase_no_backup(self):
        os.environ.pop("BACKUP_PASSPHRASE")
        self.assertIn("skipped", self.run_backup())
        self.assertEqual(self.store, {})

    def test_rows_added_during_the_export_are_fine_fewer_are_not(self):
        self.assertEqual(B.compare({"users": 2}, {"users": 3}), [])
        self.assertEqual(B.compare({"users": 2}, {"users": 1}), ["users: D1 2 行・控え 1 行"])
        self.assertEqual(B.local_counts(SQL, ["users", "works"]), {"users": 2, "works": 1})


if __name__ == "__main__":
    unittest.main()
