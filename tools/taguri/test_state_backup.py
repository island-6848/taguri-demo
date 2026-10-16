#!/usr/bin/env python3
"""Offline snapshot acceptance tests; temporary databases, no host/network access."""
from __future__ import annotations
import contextlib
from contextlib import closing
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/lib'), str(ROOT / 'tools/taguri'), str(ROOT / 'tools/review')]
import state_backup as B
import taguri_state as S
import auth as A
import rate_performances as R
import recommendation_exposure as EX


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.tmp = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.state = self.tmp / 'state'
        self.root = self.tmp / 'repo'
        self.root.mkdir()
        self.snapshot = self.tmp / 'snapshot'
        self.restored = self.tmp / 'restored'
        self.stack.enter_context(patch.dict(os.environ, {'TAGURI_STATE_DIR': str(self.state)}))
        self.stack.enter_context(patch.object(S, 'ROOT', self.root))
        self.stack.enter_context(patch.object(B, 'ROOT', self.root))
        self.stack.enter_context(patch.object(A, 'DB_PATH', S.auth_path()))
        self.stack.enter_context(patch.object(A, 'PEPPER_PATH', S.pepper_path()))
        self.stack.enter_context(patch.object(R, 'DB', S.ratings_path()))
        self.logs = io.StringIO()
        self.stack.enter_context(contextlib.redirect_stdout(self.logs))
        self.stack.enter_context(contextlib.redirect_stderr(self.logs))
        S.prepare_storage()
        self.code = A.generate_recovery_code()
        self.uid, _ = A.access_or_register(self.code)
        self.token = A.create_session(self.uid)
        with closing(R.connect()) as con, con:
            con.execute("INSERT INTO works(user_id,work_key,title,updated_at,verdict,note_impression) VALUES(?,?,?,'now','◎','PRIVATE-STORY')", (self.uid, 'work', 'PRIVATE-TITLE'))
            # Latest releases can introduce tables; snapshots must retain them.
            con.execute('CREATE TABLE future_schema(value TEXT)')
            con.execute("INSERT INTO future_schema VALUES('schema survives')")
        with closing(sqlite3.connect(S.exposure_path())) as exposure, exposure:
            EX.Store(exposure)
            exposure.execute("INSERT INTO recommendation_presentations VALUES('presentation','snapshot-user','now','[]','v1','recommend','current')")
        self.addCleanup(self.stack.close)

    def backup(self):
        B.backup_state(self.snapshot, server_stopped=True)

    def refresh_hash(self, relative):
        path = self.snapshot / 'manifest.json'
        data = json.loads(path.read_text())
        data['files'][relative] = B._digest(self.snapshot / relative)
        path.write_text(json.dumps(data))

    def test_legacy_v1_requires_explicit_override(self):
        self.backup()
        (self.snapshot / 'recommendation_exposure.db').unlink()
        manifest = json.loads((self.snapshot / 'manifest.json').read_text())
        manifest['format'] = B.LEGACY_FORMAT
        del manifest['files']['recommendation_exposure.db']
        (self.snapshot / 'manifest.json').write_text(json.dumps(manifest))
        with self.assertRaises(B.BackupError):
            B.restore_state(self.snapshot, self.restored, server_stopped=True)
        B.restore_state(self.snapshot, self.restored, server_stopped=True, allow_legacy_without_exposure=True)
        self.assertTrue((self.restored / 'auth/auth.db').exists())
        self.assertFalse((self.restored / 'recommendation_exposure.db').exists())
        self.assertEqual(B.main(['restore', '--backup', str(self.snapshot), '--target', str(self.tmp / 'cli-v1'), '--server-stopped', '--allow-legacy-without-exposure']), 0)

    def test_exposure_committed_wal_survives_snapshot(self):
        con = sqlite3.connect(S.exposure_path())
        self.addCleanup(con.close)
        con.execute('PRAGMA journal_mode=WAL')
        con.execute('PRAGMA wal_autocheckpoint=0')
        con.execute("INSERT INTO recommendation_presentations VALUES('wal-presentation','wal-user','now','[]','v1','recommend','current')")
        con.commit()
        self.backup()
        with closing(sqlite3.connect(self.snapshot / 'recommendation_exposure.db')) as copied, copied:
            self.assertEqual(copied.execute("SELECT user_id FROM recommendation_presentations WHERE presentation_id='wal-presentation'").fetchone()[0], 'wal-user')
            self.assertEqual(copied.execute('PRAGMA journal_mode').fetchone()[0], 'delete')

    def test_exposure_required_and_corruption_rejected(self):
        path = S.exposure_path()
        before = path.read_bytes()
        path.unlink()
        with self.assertRaises(B.BackupError):
            self.backup()
        path.write_bytes(b'corrupt telemetry')
        with self.assertRaises((sqlite3.Error, B.BackupError)):
            self.backup()
        path.write_bytes(before)
        with closing(sqlite3.connect(path)) as con, con:
            con.execute('DROP TABLE recommendation_contacts')
        with self.assertRaises(B.BackupError):
            self.backup()

    def test_requires_explicit_stopped_acknowledgement(self):
        with self.assertRaises(B.BackupError):
            B.backup_state(self.snapshot)
        self.backup()
        with self.assertRaises(B.BackupError):
            B.restore_state(self.snapshot, self.restored)
        self.assertFalse(self.restored.exists())

    def test_snapshot_complete_private_and_standalone(self):
        self.backup()
        files = {str(p.relative_to(self.snapshot)) for p in self.snapshot.rglob('*') if p.is_file()}
        self.assertEqual(files, set(B.FILES) | {'manifest.json'})
        for path in self.snapshot.rglob('*'):
            self.assertEqual(path.stat().st_mode & 0o777, 0o700 if path.is_dir() else 0o600)
        self.assertEqual(self.snapshot.stat().st_mode & 0o777, 0o700)
        manifest = json.loads((self.snapshot / 'manifest.json').read_text())
        self.assertEqual(manifest['format'], 'taguri-state-backup-v2')
        self.assertEqual(set(manifest['files']), set(B.FILES))
        for relative in B.FILES:
            self.assertEqual(manifest['files'][relative], B._digest(self.snapshot / relative))

    def test_real_auth_and_history_restore_in_fresh_process(self):
        self.backup()
        B.restore_state(self.snapshot, self.restored, server_stopped=True)
        code = "import sys;sys.path[:0]=" + repr([str(ROOT / 'tools/lib'),str(ROOT / 'tools/taguri'),str(ROOT / 'tools/review')]) + ";import auth as a,rate_performances as r;code,uid,token=" + repr((self.code,self.uid,self.token)) + "; assert a.access_or_register(code)==(uid,False);assert a.resolve_session(token)==uid;con=r.connect();w=r.read_works(con,user_id=uid)['work'];assert w['verdict']=='◎' and w['note_impression']=='PRIVATE-STORY';assert not r.read_works(con,user_id='another');assert con.execute('SELECT value FROM future_schema').fetchone()[0]=='schema survives';con.close();import sqlite3,taguri_state as s;e=sqlite3.connect(s.exposure_path());assert e.execute('SELECT user_id FROM recommendation_presentations').fetchone()[0]=='snapshot-user';e.close()"
        env = dict(os.environ, TAGURI_STATE_DIR=str(self.restored))
        result = subprocess.run([sys.executable,'-c',code],env=env,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout,'')

    def test_existing_empty_restore_destination_allowed(self):
        self.backup()
        self.restored.mkdir()
        B.restore_state(self.snapshot,self.restored,server_stopped=True)
        self.assertTrue((self.restored / 'auth/auth.db').exists())
        for path in self.restored.rglob('*'):
            self.assertEqual(path.stat().st_mode & 0o777, 0o700 if path.is_dir() else 0o600)

    def test_existing_restore_data_and_backup_destination_never_overwritten(self):
        self.backup()
        before = (self.snapshot / 'manifest.json').read_bytes()
        with self.assertRaises(B.BackupError):
            self.backup()
        self.assertEqual((self.snapshot / 'manifest.json').read_bytes(),before)
        self.restored.mkdir()
        sentinel = self.restored / 'existing'
        sentinel.write_text('keep')
        with self.assertRaises(B.BackupError):
            B.restore_state(self.snapshot,self.restored,server_stopped=True)
        self.assertEqual(sentinel.read_text(),'keep')

    def test_wal_committed_rows_and_extra_schema_survive(self):
        con = sqlite3.connect(S.ratings_path())
        self.addCleanup(con.close)
        con.execute('PRAGMA journal_mode=WAL')
        con.execute('PRAGMA wal_autocheckpoint=0')
        con.execute("INSERT INTO future_schema VALUES('wal survives')")
        con.commit()
        self.backup()
        with closing(sqlite3.connect(self.snapshot / 'review/ratings.db')) as copied, copied:
            self.assertEqual(copied.execute('SELECT count(*) FROM future_schema').fetchone()[0],2)
            self.assertEqual(copied.execute('PRAGMA journal_mode').fetchone()[0],'delete')
        self.assertFalse((self.snapshot / 'review/ratings.db-wal').exists())

    def test_missing_and_invalid_source_pepper_rejected(self):
        for value in (None,'','a','private-secret','a' * 300):
            if value is None:
                S.pepper_path().unlink()
            else:
                S.pepper_path().write_text(value)
            with self.subTest(value=value), self.assertRaises(B.BackupError):
                self.backup()
            self.assertFalse(self.snapshot.exists())

    def test_corrupt_source_database_rejected(self):
        S.ratings_path().write_bytes(b'PRIVATE-CORRUPT')
        with self.assertRaises((sqlite3.Error,B.BackupError)):
            self.backup()
        self.assertFalse(self.snapshot.exists())

    def test_wrong_source_schema_rejected(self):
        with closing(sqlite3.connect(S.auth_path())) as con, con:
            con.execute('DROP TABLE sessions')
        with self.assertRaises(B.BackupError):
            self.backup()

    def test_foreign_key_violation_rejected(self):
        with closing(sqlite3.connect(S.ratings_path())) as con, con:
            con.executescript('CREATE TABLE parent(id INTEGER PRIMARY KEY);CREATE TABLE orphan(id INTEGER REFERENCES parent(id));INSERT INTO orphan VALUES(123);')
        with self.assertRaises(B.BackupError):
            self.backup()

    def test_tampered_snapshot_checksum_rejected(self):
        self.backup()
        (self.snapshot / 'auth/auth_pepper.txt').write_text('bb' * 32)
        with self.assertRaises(B.BackupError):
            B.restore_state(self.snapshot,self.restored,server_stopped=True)
        self.assertFalse(self.restored.exists())

    def test_missing_snapshot_file_rejected(self):
        self.backup()
        (self.snapshot / 'auth/auth_pepper.txt').unlink()
        with self.assertRaises(B.BackupError):
            B.restore_state(self.snapshot,self.restored,server_stopped=True)

    def test_matching_checksum_still_requires_valid_key_and_database(self):
        self.backup()
        key = self.snapshot / 'auth/auth_pepper.txt'
        key.write_text('bad key')
        self.refresh_hash('auth/auth_pepper.txt')
        with self.assertRaises(B.BackupError):
            B.restore_state(self.snapshot,self.restored,server_stopped=True)
        key.write_text(S.pepper_path().read_text())
        self.refresh_hash('auth/auth_pepper.txt')
        (self.snapshot / 'review/ratings.db').write_bytes(b'bad database')
        self.refresh_hash('review/ratings.db')
        with self.assertRaises((sqlite3.Error,B.BackupError)):
            B.restore_state(self.snapshot,self.restored,server_stopped=True)
        self.assertFalse(self.restored.exists())

    def test_unexpected_sidecars_and_symlinks_rejected(self):
        self.backup()
        extra = self.snapshot / 'review/ratings.db-wal'
        extra.write_bytes(b'extra')
        with self.assertRaises(B.BackupError):
            B.restore_state(self.snapshot,self.restored,server_stopped=True)
        extra.unlink()
        key = self.snapshot / 'auth/auth_pepper.txt'
        key.unlink()
        key.symlink_to(S.pepper_path())
        with self.assertRaises(B.BackupError):
            B.restore_state(self.snapshot,self.restored,server_stopped=True)

    def test_relative_overlapping_and_link_destinations_rejected(self):
        self.backup()
        link = self.tmp / 'link'
        link.symlink_to(self.state,target_is_directory=True)
        for destination in (Path('relative'),self.root / 'data',self.state / 'auth/new',link):
            with self.subTest(destination=str(destination)),self.assertRaises(B.BackupError):
                B.backup_state(destination,server_stopped=True)
        with self.assertRaises(B.BackupError):
            B.restore_state(self.snapshot,self.snapshot / 'nested',server_stopped=True)

    def test_empty_mount_itself_restore_rejected(self):
        self.backup()
        self.restored.mkdir()
        with patch('os.path.ismount',return_value=True),self.assertRaises(B.BackupError):
            B.restore_state(self.snapshot,self.restored,server_stopped=True)
        self.assertTrue(self.restored.exists())

    def test_backup_failure_preserves_originals_and_cleans_staging(self):
        before = {relative:(self.state / relative).read_bytes() for relative in B.FILES}
        with patch.object(B.shutil,'copyfile',side_effect=OSError('PRIVATE-FAILURE')):
            with self.assertRaises(OSError):
                self.backup()
        self.assertFalse(self.snapshot.exists())
        self.assertEqual(list(self.tmp.glob('.taguri-backup-*')),[])
        for relative,value in before.items():
            self.assertEqual((self.state / relative).read_bytes(),value)

    def test_restore_publish_failure_protects_empty_target_and_snapshot(self):
        self.backup()
        self.restored.mkdir()
        before = (self.snapshot / 'manifest.json').read_bytes()
        with patch.object(B,'_publish',side_effect=OSError('PRIVATE-FAILURE')):
            with self.assertRaises(OSError):
                B.restore_state(self.snapshot,self.restored,server_stopped=True)
        self.assertTrue(self.restored.exists())
        self.assertEqual(list(self.restored.iterdir()),[])
        self.assertEqual((self.snapshot / 'manifest.json').read_bytes(),before)
        self.assertEqual(list(self.tmp.glob('.taguri-restore-*')),[])

    def test_snapshot_changed_during_copy_rejected(self):
        self.backup()
        original = B.shutil.copyfile
        def copy(source,destination):
            if str(source).endswith('auth_pepper.txt'):
                Path(source).write_text('cd' * 32)
            return original(source,destination)
        with patch.object(B.shutil,'copyfile',copy):
            # Copying changed bytes after validation must be rejected.
            with self.assertRaises(B.BackupError):
                B.restore_state(self.snapshot,self.restored,server_stopped=True)
        self.assertFalse(self.restored.exists())

    def test_cli_fixed_logs_without_sensitive_values_on_success_and_failure(self):
        self.logs.seek(0);self.logs.truncate()
        self.assertEqual(B.main(['backup','--output',str(self.snapshot),'--server-stopped']),0)
        self.assertEqual(B.main(['restore','--backup',str(self.snapshot),'--target',str(self.restored),'--server-stopped']),0)
        self.assertEqual(B.main(['backup','--output','PRIVATE-CLI-SECRET','--server-stopped']),1)
        self.assertEqual(B.main(['PRIVATE-CLI-SECRET']),1)
        log = self.logs.getvalue()
        for secret in (self.code,self.uid,self.token,'PRIVATE-STORY','PRIVATE-TITLE','PRIVATE-CLI-SECRET',str(self.tmp),S.pepper_path().read_text()):
            self.assertNotIn(secret,log)
        records = [json.loads(line) for line in log.splitlines()]
        self.assertEqual(len(records),4)
        self.assertTrue(all(set(record)=={'event','operation','outcome'} for record in records))

    def test_cli_corrupt_database_failure_has_no_traceback_or_secret(self):
        S.ratings_path().write_bytes(b'PRIVATE-CORRUPT')
        self.logs.seek(0);self.logs.truncate()
        self.assertEqual(B.main(['backup','--output',str(self.snapshot),'--server-stopped']),1)
        self.assertNotIn('Traceback',self.logs.getvalue())
        self.assertNotIn('PRIVATE-CORRUPT',self.logs.getvalue())


if __name__=='__main__':
    unittest.main()
