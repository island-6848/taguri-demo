import datetime
import importlib.util
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'scripts'))
spec = importlib.util.spec_from_file_location('deliver_catalogue', HERE / 'scripts' / 'deliver_catalogue.py')
D = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D)
TODAY = datetime.date(2026, 10, 14)


def stage(sid, title, period, **kw):
    return {'stage_id': sid, 'title': title, 'period': period, 'group': '劇団', 'theater': '劇場',
            'fields': {'出演': '俳優', '公式／劇場サイト': 'https://example.com/x ほか'}, **kw}


class DeliverTest(unittest.TestCase):
    def setUp(self):
        self.data = Path(tempfile.mkdtemp())
        (self.data / 'review').mkdir()
        (self.data / 'credits').mkdir()
        self.write([stage('1', 'これから', '2026/11/01 (日) ～ 2026/11/09 (月)', why_b=['private']),
                    stage('2', '終わった', '2026/09/01 (火) ～ 2026/09/05 (土)'),
                    stage('3', '印付きで終わった', '2026/12/01 ～ 2026/12/02', ended=True),
                    stage('4', '期間なし', '')])
        (self.data / 'review' / 'candidates_scan.json').write_text(json.dumps({'date': '2026-10-13T20:00'}))
        (self.data / 'credits' / 'themes.jsonl').write_text(
            json.dumps({'side': 'candidate', 'id': '1', 'synopsis': '三姉妹の話', 'elements': [{'kind': '題材', 'word': '家族'}]},
                       ensure_ascii=False) + '\n' +
            json.dumps({'side': 'rated', 'id': '1', 'synopsis': '別の側', 'elements': []}, ensure_ascii=False) + '\n')
        self.out = self.data / 'out'
        self.db = sqlite3.connect(':memory:')
        for f in sorted((HERE / 'migrations').glob('*.sql')):
            self.db.executescript(f.read_text(encoding='utf-8'))

    def write(self, rows):
        (self.data / 'review' / 'candidates.jsonl').write_text(
            ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8')

    def deliver(self, **kw):
        report = D.build(self.data, self.out, TODAY, False, kw.get('budget', D.WRITE_BUDGET))
        self.db.executescript((self.out / 'catalogue.sql').read_text(encoding='utf-8'))
        D.commit(self.data, self.out)
        return report

    def test_upcoming_public_rows_with_synopsis(self):
        report = self.deliver()
        self.assertEqual((report['stages'], report['changed'], report['with_synopsis']), (1, 1, 1))
        sid, url, meta = self.db.execute('SELECT id,url,metadata FROM catalogue').fetchone()
        meta = json.loads(meta)
        self.assertEqual((sid, url), ('1', 'https://example.com/x'))
        self.assertEqual((meta['synopsis'], meta['words'], meta['end_date']), ('三姉妹の話', ['家族'], '2026-11-09'))
        self.assertNotIn('why_b', meta)
        m = dict(self.db.execute("SELECT k,v FROM rec_meta").fetchall())
        self.assertEqual((m['catalogue_scan'], m['catalogue_upcoming']), ('2026-10-13', '1'))

    def test_line_separator_inside_a_title(self):
        # 2026-10-13 の毎日の実行は、題名の中の U+2028 を splitlines が行の区切りとみなして落ちた
        self.write([stage('1', 'これから\u2028二部', '2026/11/01 ～ 2026/11/09')])
        report = self.deliver()
        self.assertEqual(report['stages'], 1)
        self.assertEqual(self.db.execute('SELECT title FROM catalogue').fetchone()[0], 'これから\u2028二部')

    def test_second_delivery_writes_only_changes_and_never_deletes(self):
        self.deliver()
        self.assertEqual(self.deliver()['changed'], 0)
        self.write([stage('1', 'これから（改題）', '2026/11/01 ～ 2026/11/09'),
                    stage('5', '新しい', '2026/12/01 ～ 2026/12/03')])
        self.assertEqual(self.deliver()['changed'], 2)
        self.write([stage('5', '新しい', '2026/12/01 ～ 2026/12/03')])
        self.deliver()
        self.assertEqual(sorted(r[0] for r in self.db.execute('SELECT id FROM catalogue')), ['1', '5'])

    def test_uncommitted_delivery_is_sent_again(self):
        D.build(self.data, self.out, TODAY, False, D.WRITE_BUDGET)      # wrangler failed: no commit
        self.assertEqual(D.build(self.data, self.out, TODAY, False, D.WRITE_BUDGET)['changed'], 1)

    def test_write_budget_stops_before_upload(self):
        with self.assertRaises(SystemExit):
            D.build(self.data, self.out, TODAY, False, 1)


if __name__ == '__main__':
    unittest.main()
