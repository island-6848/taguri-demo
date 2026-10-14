"""deliver_past: only new lines are sent, the budget caps a day, rows load into past_stage."""
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / 'scripts' / 'deliver_past.py'
MIGRATION = HERE.parent / 'migrations' / '0012.sql'

ROWS = [
    {"stage_id": "30", "title": "夜の果て", "start": "2024-03-01", "end": "2024-03-10", "theater": "本多劇場",
     "group": "劇団あおば", "pref": "東京都", "fields": {"出演": "山田太郎、鈴木花子", "演出": "佐藤一郎"}},
    {"stage_id": "20", "title": "O'Neill の夜\u2028第二部", "start": "2022-07-01", "end": "2022-07-03", "fields": {}},
]


def run(*args):
    return json.loads(subprocess.run([sys.executable, str(SCRIPT), *args], check=True,
                                     capture_output=True, text=True).stdout.strip().splitlines()[-1]) \
        if args[0] == 'build' else subprocess.run([sys.executable, str(SCRIPT), *args], check=True)


class DeliverPastTest(unittest.TestCase):
    def test_incremental_upload(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            (d / 'past').mkdir()
            (d / 'past' / 'stages.jsonl').write_text('\n'.join(json.dumps(r, ensure_ascii=False) for r in ROWS) + '\n',
                                                     encoding='utf-8')
            con = sqlite3.connect(d / 'd1.db')
            con.executescript('CREATE TABLE works(user_id TEXT, work_key TEXT, title TEXT, first_date TEXT, stage_id TEXT);')
            con.executescript(MIGRATION.read_text(encoding='utf-8'))
            first = run('build', '--data', t, '--out', str(d / 'out'), '--budget', '2')
            self.assertEqual((first['rows'], first['left']), (1, 1))
            con.executescript((d / 'out' / 'past-upload.sql').read_text(encoding='utf-8'))
            # Not committed yet: the same row is built again (a failed upload is retried).
            self.assertEqual(run('build', '--data', t, '--out', str(d / 'out'), '--budget', '2')['delivered_before'], 0)
            run('commit', '--data', t, '--out', str(d / 'out'))
            second = run('build', '--data', t, '--out', str(d / 'out'))
            self.assertEqual((second['rows'], second['left'], second['delivered_before']), (1, 0, 1))
            con.executescript((d / 'out' / 'past-upload.sql').read_text(encoding='utf-8'))
            got = dict(con.execute('SELECT stage_id, tkey FROM past_stage').fetchall())
            self.assertEqual(got, {'30': '夜の果て', '20': 'oneillの夜第二部'})
            people = json.loads(con.execute("SELECT people FROM past_stage WHERE stage_id='30'").fetchone()[0])
            self.assertIn(['出演', '山田太郎'], people)
            cols = [r[1] for r in con.execute('PRAGMA table_info(works)')]
            self.assertIn('stage_auto', cols)
            self.assertIn('stage_off', cols)


class StatementSizeTest(unittest.TestCase):
    def test_statements_fit_d1_in_bytes(self):
        # 2026-10-14: 文字数で数えていたので、日本語の多い 7,016 行が SQLITE_TOOBIG で断られた
        sys.path.insert(0, str(HERE.parent / 'scripts'))
        import build_recommend_index as BI
        rows = [(str(i), '夜の果ての劇場' * 20, '出演' * 300) for i in range(400)]
        stmts = BI._inserts('past_stage', 'stage_id,title,people', rows)
        self.assertGreater(len(stmts), 1)
        self.assertTrue(all(len(x.encode('utf-8')) <= BI.MAX_STATEMENT_BYTES for x in stmts))
        self.assertEqual(sum(x.count("('") for x in stmts), 400)


if __name__ == '__main__':
    unittest.main()
