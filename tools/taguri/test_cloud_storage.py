#!/usr/bin/env python3
"""Independent state/catalog/log acceptance tests; no network or live DB writes."""
from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools/lib"), str(ROOT / "tools/taguri")]
import taguri_state as ST
import serve_cloud as CLOUD
from test_demo_stability import DemoStabilityTests, APP


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.tmp = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.root = self.tmp / "repo"
        self.root.mkdir()
        self.home = self.tmp / "home"
        self.target = self.tmp / "state"
        self.stack.enter_context(patch.object(ST, "ROOT", self.root))
        self.stack.enter_context(patch.object(CLOUD, "ROOT", self.root))
        self.stack.enter_context(patch.object(Path, "home", return_value=self.home))
        self.stack.enter_context(patch.dict(os.environ, {"TAGURI_STATE_DIR": str(self.target),
                                                        "TAGURI_MIGRATE_LEGACY_STATE": "0"}))
        self.logs = io.StringIO()
        self.stack.enter_context(contextlib.redirect_stdout(self.logs))
        self.addCleanup(self.stack.close)

    def legacy(self, *, pepper=True):
        for rel in ("auth/auth.db", "review/ratings.db"):
            path = self.root / "data" / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(path) as con:
                con.execute("CREATE TABLE users(user_id TEXT)")
                con.execute("INSERT INTO users VALUES('private-user')")
        if pepper:
            key = self.home / ".config/taguri/auth_pepper.txt"
            key.parent.mkdir(parents=True)
            key.write_text("ab" * 32)

    def archive(self, members):
        path = self.tmp / "catalog.tar"
        with tarfile.open(path, "w") as tf:
            for name, value in members.items():
                member = tarfile.TarInfo(name)
                if value is None:
                    member.type = tarfile.SYMTYPE
                    member.linkname = "/etc/passwd"
                    tf.addfile(member)
                else:
                    data = value.encode()
                    member.size = len(data)
                    tf.addfile(member, io.BytesIO(data))
        return path

    def test_temporary_status_does_not_claim_persistence(self):
        with patch.dict(os.environ, {"TAGURI_STATE_DIR": ""}):
            ST.prepare_storage()
            self.assertEqual(ST.storage_status()["mode"], "temporary")
            self.assertFalse(ST.storage_status()["persistent_mount_required"])
            self.assertEqual(ST.ratings_path(), self.root / "data/review/ratings.db")
        self.assertIn('"outcome": "temporary"', self.logs.getvalue())

    def test_configured_paths_are_separate_and_private(self):
        ST.prepare_storage()
        self.assertEqual(ST.ratings_path(), self.target / "review/ratings.db")
        self.assertEqual(ST.auth_path(), self.target / "auth/auth.db")
        self.assertEqual(ST.pepper_path(), self.target / "auth/auth_pepper.txt")
        self.assertEqual(self.target.stat().st_mode & 0o777, 0o700)
        self.assertTrue(ST.storage_status()["persistent_mount_required"])

    def test_invalid_overlapping_paths_rejected(self):
        for path in ("relative", self.root, self.root / "data", self.root / "data/state"):
            with self.subTest(path=str(path)), patch.dict(os.environ, {"TAGURI_STATE_DIR": str(path)}):
                with self.assertRaises(RuntimeError):
                    ST.prepare_storage()

    def test_legacy_without_explicit_migration_stops(self):
        self.legacy()
        with self.assertRaises(RuntimeError):
            ST.prepare_storage()
        self.assertFalse(self.target.exists())
        self.assertTrue((self.root / "data/review/ratings.db").exists())

    def test_migration_preserves_db_and_pepper_and_is_repeatable(self):
        self.legacy()
        with patch.dict(os.environ, {"TAGURI_MIGRATE_LEGACY_STATE": "1"}):
            ST.prepare_storage()
            with sqlite3.connect(ST.ratings_path()) as con:
                self.assertEqual(con.execute("SELECT user_id FROM users").fetchone()[0], "private-user")
                con.execute("INSERT INTO users VALUES('new-user')")
            ST.prepare_storage()
        with sqlite3.connect(ST.ratings_path()) as con:
            self.assertEqual(con.execute("SELECT count(*) FROM users").fetchone()[0], 2)
        self.assertEqual(ST.pepper_path().read_text(), "ab" * 32)
        self.assertTrue((self.root / "data/auth/auth.db").exists())
        self.assertEqual(ST.pepper_path().stat().st_mode & 0o777, 0o600)

    def test_existing_empty_directory_migrates(self):
        self.legacy()
        self.target.mkdir()
        with patch.dict(os.environ, {"TAGURI_MIGRATE_LEGACY_STATE": "1"}):
            ST.prepare_storage()
        self.assertTrue(ST.auth_path().exists())
        self.assertTrue(ST.pepper_path().exists())

    def test_mount_itself_is_not_replaced(self):
        self.legacy()
        self.target.mkdir()
        with patch.dict(os.environ, {"TAGURI_MIGRATE_LEGACY_STATE": "1"}), patch("os.path.ismount", return_value=True):
            with self.assertRaises(RuntimeError):
                ST.prepare_storage()
        self.assertTrue(self.target.exists())

    def test_missing_or_invalid_legacy_pepper_stops(self):
        self.legacy(pepper=False)
        with patch.dict(os.environ, {"TAGURI_MIGRATE_LEGACY_STATE": "1"}):
            with self.assertRaises(RuntimeError):
                ST.prepare_storage()
            key = self.home / ".config/taguri/auth_pepper.txt"
            key.parent.mkdir(parents=True)
            for value in ("", "invalid-private-secret", "ab"):
                key.write_text(value)
                with self.assertRaises(RuntimeError):
                    ST.prepare_storage()
        self.assertFalse(ST.auth_path().exists())
        self.assertNotIn("invalid-private-secret", self.logs.getvalue())

    def test_partial_destination_never_silently_discards_legacy(self):
        self.legacy()
        self.target.mkdir()
        (self.target / "unrelated").write_text("do not overwrite")
        with patch.dict(os.environ, {"TAGURI_MIGRATE_LEGACY_STATE": "1"}):
            with self.assertRaises(RuntimeError):
                ST.prepare_storage()
        self.assertEqual((self.target / "unrelated").read_text(), "do not overwrite")

    def test_failed_migration_keeps_sources_and_cleans_staging(self):
        self.legacy()
        original = (self.root / "data/review/ratings.db").read_bytes()
        with patch.dict(os.environ, {"TAGURI_MIGRATE_LEGACY_STATE": "1"}), patch.object(ST.shutil, "copyfile", side_effect=OSError("private-secret")):
            with self.assertRaises(RuntimeError) as caught:
                ST.prepare_storage()
        self.assertEqual((self.root / "data/review/ratings.db").read_bytes(), original)
        self.assertFalse(self.target.exists())
        self.assertEqual(list(self.tmp.glob(".taguri-state-*")), [])
        self.assertNotIn("private-secret", str(caught.exception) + self.logs.getvalue())

    def test_migration_includes_committed_wal(self):
        self.legacy()
        con = sqlite3.connect(self.root / "data/review/ratings.db")
        self.addCleanup(con.close)
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA wal_autocheckpoint=0")
        con.execute("INSERT INTO users VALUES('wal-user')")
        con.commit()
        with patch.dict(os.environ, {"TAGURI_MIGRATE_LEGACY_STATE": "1"}):
            ST.prepare_storage()
        with sqlite3.connect(ST.ratings_path()) as copied:
            self.assertEqual(copied.execute("SELECT count(*) FROM users").fetchone()[0], 2)

    def test_unwritable_probe_stops_without_secret_trace(self):
        with patch.object(ST.tempfile, "TemporaryFile", side_effect=PermissionError("secret-path")):
            with self.assertRaises(RuntimeError) as caught:
                ST.prepare_storage()
        self.assertNotIn("secret-path", str(caught.exception) + self.logs.getvalue())

    def test_catalog_replaces_shared_files_preserves_state_excludes_archive_db(self):
        self.legacy()
        old = self.root / "data/review/old.json"
        old.write_text("old")
        before = (self.root / "data/review/ratings.db").read_bytes()
        archive = self.archive({"review/candidates.jsonl": "new candidates", "review/ratings.db": "untrusted DB", "auth/auth.db": "untrusted auth", "auth/auth_pepper.txt": "bad key"})
        CLOUD._install_catalog(archive)
        self.assertEqual((self.root / "data/review/candidates.jsonl").read_text(), "new candidates")
        self.assertFalse(old.exists())
        self.assertEqual((self.root / "data/review/ratings.db").read_bytes(), before)
        with sqlite3.connect(self.root / "data/auth/auth.db") as con:
            self.assertEqual(con.execute("SELECT user_id FROM users").fetchone()[0], "private-user")
        self.assertFalse((self.root / "data/auth/auth_pepper.txt").exists())

    def test_catalog_rejects_traversal_absolute_and_symlink_without_damage(self):
        self.legacy()
        for name, value in (("../escape", "bad"), ("/tmp/absolute", "bad"), ("review/link", None)):
            with self.subTest(name=name):
                archive = self.archive({"review/candidates.jsonl": "candidate", name: value})
                with self.assertRaises(ValueError):
                    CLOUD._install_catalog(archive)
                self.assertTrue((self.root / "data/review/ratings.db").exists())
                self.assertFalse((self.root / "data/review/candidates.jsonl").exists())

    def test_missing_candidate_keeps_catalog(self):
        old = self.root / "data/review/candidates.jsonl"
        old.parent.mkdir(parents=True)
        old.write_text("old")
        with self.assertRaises(ValueError):
            CLOUD._install_catalog(self.archive({"review/other.json": "x"}))
        self.assertEqual(old.read_text(), "old")

    def test_catalog_exchange_failure_rolls_back(self):
        old = self.root / "data/review/candidates.jsonl"
        old.parent.mkdir(parents=True)
        old.write_text("old")
        original = Path.rename
        def rename(path, dest):
            if path.name == "new":
                raise OSError("private-secret")
            return original(path, dest)
        with patch.object(Path, "rename", rename):
            with self.assertRaises(OSError):
                CLOUD._install_catalog(self.archive({"review/candidates.jsonl": "new"}))
        self.assertEqual(old.read_text(), "old")

    def test_failed_download_is_redacted_and_keeps_catalog(self):
        old = self.root / "data/review/candidates.jsonl"
        old.parent.mkdir(parents=True)
        old.write_text("old")
        from types import SimpleNamespace
        with patch.dict(sys.modules, {"boto3": SimpleNamespace(client=lambda *a, **k: (_ for _ in ()).throw(OSError("secret-token")))}):
            with self.assertRaises(RuntimeError) as caught:
                CLOUD._fetch_catalog()
        self.assertEqual(old.read_text(), "old")
        self.assertNotIn("secret-token", str(caught.exception) + self.logs.getvalue())

    def test_events_allow_fixed_fields_and_broken_sink_is_safe(self):
        ST.event("write_result", operation="note", status=200)
        record = json.loads(self.logs.getvalue())
        self.assertEqual(set(record), {"timestamp", "event", "outcome", "operation", "status"})
        for kwargs in ({"name": "private-note"}, {"name": "write_result", "operation": "private-note"}):
            with self.assertRaises(ValueError):
                ST.event(**kwargs)
        with patch("builtins.print", side_effect=BrokenPipeError):
            ST.event("write_result", operation="note", status=200)

    def test_existing_auth_requires_intact_pepper(self):
        self.target.mkdir()
        auth = ST.auth_path()
        auth.parent.mkdir()
        with sqlite3.connect(auth) as con:
            con.execute("CREATE TABLE users(user_id TEXT)")
            con.execute("INSERT INTO users VALUES('existing')")
        for value in (None, "", "not-hex", "ab"):
            if value is not None:
                ST.pepper_path().write_text(value)
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                ST.prepare_storage()
        self.assertEqual(ST.pepper_path().read_text(), "ab")

    def test_concurrent_first_auth_publishes_one_complete_pepper(self):
        import auth
        from concurrent.futures import ThreadPoolExecutor
        ST.prepare_storage()
        with patch.object(auth, "DB_PATH", ST.auth_path()), patch.object(auth, "PEPPER_PATH", ST.pepper_path()):
            with ThreadPoolExecutor(max_workers=8) as pool:
                keys = list(pool.map(lambda _: auth._pepper(), range(16)))
        self.assertEqual(len(set(keys)), 1)
        self.assertEqual(len(keys[0]), 32)
        self.assertEqual(ST.pepper_path().stat().st_mode & 0o777, 0o600)

    def test_external_state_untouched_by_catalog_refresh(self):
        ST.prepare_storage()
        ST.ratings_path().write_bytes(b"private state sentinel")
        ST.pepper_path().write_text("ab" * 32)
        CLOUD._install_catalog(self.archive({"review/candidates.jsonl": "new", "review/ratings.db": "bad"}))
        self.assertEqual(ST.ratings_path().read_bytes(), b"private state sentinel")
        self.assertEqual(ST.pepper_path().read_text(), "ab" * 32)
        self.assertFalse((self.root / "data/review/ratings.db").exists())

    def test_actual_modules_share_state_paths(self):
        script = "import sys; sys.path[:0]=" + repr([str(ROOT / "tools/lib"), str(ROOT / "tools/taguri"), str(ROOT / "tools/review"), str(ROOT / "tools/tickets")]) + "; import taguri_state as s, auth, app, feedback, rate_performances, impressions, reasons, corrections; assert auth.DB_PATH==s.auth_path(); assert auth.PEPPER_PATH==s.pepper_path(); assert all(m.DB==s.ratings_path() for m in (app, feedback, rate_performances, impressions, reasons, corrections))"
        result = subprocess.run([sys.executable, "-c", script], env=os.environ.copy(), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_separate_process_restart_preserves_real_auth_and_rating(self):
        paths = repr([str(ROOT / "tools/lib"), str(ROOT / "tools/taguri"), str(ROOT / "tools/review")])
        prefix = "import sys,json; sys.path[:0]=" + paths + "; import taguri_state as s, auth as a, rate_performances as r; s.ROOT=__import__('pathlib').Path(" + repr(str(self.root)) + "); s.prepare_storage(); "
        writer = prefix + "code=a.generate_recovery_code(); uid,_=a.access_or_register(code); token=a.create_session(uid); con=r.connect(); con.execute(\"INSERT INTO works(user_id,work_key,title,updated_at,verdict,note_impression) VALUES(?,?,?,'now','◎','private story')\",(uid,'work','title')); con.commit(); con.close(); print(json.dumps([code,uid,token]))"
        first = subprocess.run([sys.executable, "-c", writer], env=os.environ.copy(), capture_output=True, text=True)
        self.assertEqual(first.returncode, 0, first.stderr)
        code, uid, token = json.loads(first.stdout.splitlines()[-1])
        reader = prefix + "code,expected,token=" + repr((code, uid, token)) + "; uid,new=a.access_or_register(code); assert uid==expected and not new; assert a.resolve_session(token)==uid; con=r.connect(); row=r.read_works(con,user_id=uid)['work']; assert row['verdict']=='◎' and row['note_impression']=='private story'; assert not r.read_works(con,user_id='other'); con.close()"
        second = subprocess.run([sys.executable, "-c", reader], env=os.environ.copy(), capture_output=True, text=True)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertNotIn("private story", first.stdout + second.stdout)


class OperationalHTTPTests(DemoStabilityTests):
    def test_health_does_not_register_or_expose_secrets(self):
        from test_demo_stability import AU
        with patch.object(AU, "access_or_register", side_effect=AssertionError("health registered user")):
            status, result = self.request("/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(result["storage"]["version"], "state-storage-v1")
        self.assertNotIn("welcome_code", result)
        self.assertNotIn("auth_pepper", json.dumps(result))

    def test_note_logs_do_not_contain_body_or_cookie(self):
        status, result = self.request("/api/add_work", body={"title": "private title", "date": "2020-01-01"})
        key = result["work_key"]
        logs = io.StringIO()
        with contextlib.redirect_stdout(logs), contextlib.redirect_stderr(logs):
            status, result = self.request("/api/note", body={"work_key": key, "note_impression": "PRIVATE-NOTE-SECRET"})
        self.assertEqual(status, 200)
        self.assertNotIn("PRIVATE-NOTE-SECRET", logs.getvalue())
        self.assertNotIn(self.users[0][0], logs.getvalue())
        self.assertNotIn(self.users[0][1], logs.getvalue())
        records = [json.loads(line) for line in logs.getvalue().splitlines()]
        self.assertIn({"event": "write_result", "operation": "note", "status": 200, "outcome": "ok"}, [{k:v for k,v in rec.items() if k != "timestamp"} for rec in records])

    def test_save_failure_is_503_redacted_and_keeps_previous_value(self):
        status, result = self.request("/api/add_work", body={"title": "failure", "date": "2020-01-01"})
        key = result["work_key"]
        self.request("/api/note", body={"work_key": key, "note_impression": "previous"})
        logs = io.StringIO()
        with patch.object(APP, "save_work_field", side_effect=sqlite3.OperationalError("PRIVATE-DB-SECRET")), contextlib.redirect_stdout(logs), contextlib.redirect_stderr(logs):
            status, result = self.request("/api/note", body={"work_key": key, "note_impression": "new"})
        self.assertEqual(status, 503)
        self.assertNotIn("PRIVATE-DB-SECRET", json.dumps(result) + logs.getvalue())
        from test_demo_stability import R
        with R.connect() as con:
            self.assertEqual(R.read_works(con, user_id=self.users[0][0])[key]["note_impression"], "previous")


del DemoStabilityTests  # Avoid collecting the imported base suite twice.

if __name__ == "__main__":
    unittest.main()
