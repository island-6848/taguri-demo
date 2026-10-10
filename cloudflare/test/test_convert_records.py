import importlib.util
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'convert_records.py'
spec = importlib.util.spec_from_file_location('convert_records', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class MigrationTest(unittest.TestCase):
    def test_stable_ids_and_no_private_auth_fields(self):
        rows = [{'title': '舞台', 'date': '2026-10-24', 'time': '13:00', 'email': 'secret', 'user_id': 'private'}]
        first = module.convert(rows)
        self.assertEqual(first, module.convert(rows))
        self.assertEqual(first['records'][0]['time'], '13:00')
        self.assertNotIn('email', first['records'][0])
        self.assertNotIn('user_id', first['records'][0])

    def test_database_is_read_only_and_user_scoped(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / 'old.sqlite'
            output = Path(directory) / 'new.json'
            with sqlite3.connect(db) as con:
                con.execute('CREATE TABLE works(user_id TEXT,work_key TEXT,title TEXT,first_date TEXT,verdict TEXT,note_impression TEXT)')
                con.executemany('INSERT INTO works VALUES(?,?,?,?,?,?)', [('alice','1','自分','2026-01-01','◎','感想'), ('bob','2','秘密','2026-01-02','△','別人')])
            result = subprocess.run([sys.executable,str(SCRIPT),'--database',str(db),'--user-id','alice','--output',str(output)],capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(output.read_text())
            self.assertEqual(len(payload['records']), 1)
            self.assertEqual(payload['records'][0]['rating'], '◎')
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            with sqlite3.connect(db) as con:
                self.assertEqual(con.execute('SELECT count(*) FROM works').fetchone()[0],2)


if __name__ == '__main__':
    unittest.main()
