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

    def test_venue_prefectures_are_delivered_once_and_only_when_one(self):
        # 2026-10-15 起案者「都道府県がわからない作品しかない」: the catalogue rows carry no prefecture;
        # a venue -> prefecture table (migration 0024) gives it without rewriting the catalogue.
        self.write([stage('1', 'これから', '2026/11/01 ～ 2026/11/09', theater='劇場A', pref='東京都'),
                    stage('5', '同じ劇場', '2026/12/01 ～ 2026/12/03', theater='劇場A', pref='東京都'),
                    stage('6', '名前が同じ別の劇場', '2026/12/01 ～ 2026/12/03', theater='市民会館', pref='大阪府'),
                    stage('7', '名前が同じ別の劇場', '2026/12/04 ～ 2026/12/05', theater='市民会館', pref='愛知県'),
                    stage('8', '都道府県なし', '2026/12/01 ～ 2026/12/03', theater='劇場C')])
        self.assertEqual(self.deliver()['venues_changed'], 1)
        self.assertEqual(self.db.execute('SELECT venue,pref FROM venue_pref').fetchall(), [('劇場A', '東京都')])
        self.assertEqual(self.deliver()['venues_changed'], 0)       # nothing new: no writes
        self.write([stage('1', 'これから', '2026/11/01 ～ 2026/11/09', theater='劇場A', pref='神奈川県')])
        self.assertEqual(self.deliver()['venues_changed'], 1)
        self.assertEqual(self.db.execute('SELECT pref FROM venue_pref').fetchone()[0], '神奈川県')

    def test_write_budget_stops_before_upload(self):
        with self.assertRaises(SystemExit):
            D.build(self.data, self.out, TODAY, False, 1)


if __name__ == '__main__':
    unittest.main()


class PathsTest(unittest.TestCase):
    # The workflow passes --out ../d1-out from cloudflare/, while the index / labels / cards builders run
    # with cwd=ROOT: a relative path made them fail (FileNotFoundError) and no index ever reached D1.
    def test_relative_paths_are_made_absolute_before_building(self):
        seen = {}
        build, spend = D.build, D.FT.d1_spend
        D.build = lambda data, out, today, index, budget: seen.update(data=data, out=out) or {'writes': 0}
        D.FT.d1_spend = lambda data, n: None
        argv = sys.argv
        sys.argv = ['deliver_catalogue.py', 'build', '--data', 'some-data', '--out', '../d1-out', '--index']
        try:
            D.main()
        except SystemExit:
            pass
        finally:
            D.build, D.FT.d1_spend, sys.argv = build, spend, argv
        self.assertTrue(seen['out'].is_absolute(), seen)
        self.assertTrue(seen['data'].is_absolute(), seen)


class IndexDiffStateTest(DeliverTest):
    # 差分の索引（q-index-incremental）: 送った分のハッシュだけを、commit で次回の比べる元にする。
    def fake_index(self, rev, writes, rows):
        def run(out, data):
            (out / 'index.sql').write_text('SELECT 1;\n')
            (out / 'index-hashes.json').write_text(json.dumps({'rec_stage': {'1': rev}}))
            return rev, writes, out / 'index.sql', rows
        return run

    def deliver_index(self, rev, writes, rows, budget):
        build_index, build_labels, build_cards = D.build_index, D.build_labels, D.build_cards
        D.build_index, D.build_labels, D.build_cards = self.fake_index(rev, writes, rows), lambda out: None, lambda out, today: None
        try:
            report = D.build(self.data, self.out, TODAY, True, budget)
        finally:
            D.build_index, D.build_labels, D.build_cards = build_index, build_labels, build_cards
        D.commit(self.data, self.out)
        return report

    def test_sent_hashes_are_kept_and_skipped_ones_are_not(self):
        hashes = self.data / D.INDEX_HASHES
        r = self.deliver_index('rev1', 100, 50, D.WRITE_BUDGET)
        self.assertIn('rev1', r['index'])
        self.assertEqual(json.loads(hashes.read_text())['rec_stage']['1'], 'rev1')
        r = self.deliver_index('rev2', 10 ** 9, 50, D.WRITE_BUDGET)
        self.assertTrue(r['index'].startswith('skipped'))
        self.assertEqual(json.loads(hashes.read_text())['rec_stage']['1'], 'rev1')
        r = self.deliver_index('rev3', 0, 0, D.WRITE_BUDGET)
        self.assertEqual(r['index'], 'unchanged')
        self.assertEqual(json.loads(hashes.read_text())['rec_stage']['1'], 'rev1')
