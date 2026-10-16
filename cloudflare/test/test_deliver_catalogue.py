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


class VenueCensusTest(DeliverTest):
    """劇場制覇マップの分母（migration 0027）: 2 公演以上・ホールは分けたまま・会場でないものは除く。"""

    def past(self, rows):
        (self.data / 'past').mkdir(exist_ok=True)
        (self.data / 'past' / 'stages.jsonl').write_text(
            ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8')

    def test_census_keeps_halls_apart_and_drops_what_is_not_a_venue(self):
        self.write([stage('1', 'これから', '2026/11/01 ～ 2026/11/09', theater='東京芸術劇場 シアターイースト', pref='東京都'),
                    stage('5', '配信', '2026/12/01 ～ 2026/12/03', theater='オンライン配信', pref='東京都')])
        self.past([{'stage_id': '9', 'theater': '東京芸術劇場　シアターイースト', 'pref': '東京都'},
                   {'stage_id': '10', 'theater': '東京芸術劇場 プレイハウス', 'pref': '東京都'},
                   {'stage_id': '11', 'theater': '東京芸術劇場 プレイハウス', 'pref': '東京都'},
                   {'stage_id': '12', 'theater': '一度だけの場所', 'pref': '東京都'},
                   {'stage_id': '13', 'theater': 'オンライン配信', 'pref': '東京都'},
                   {'stage_id': '14', 'theater': '某所', 'pref': '大阪府'},
                   {'stage_id': '15', 'theater': '某所', 'pref': '大阪府'},
                   {'stage_id': '1', 'theater': '東京芸術劇場 シアターイースト', 'pref': '東京都'}])   # same stage: once
        self.assertEqual(D.venue_census(self.data), {'東京芸術劇場シアターイースト': '東京都', '東京芸術劇場プレイハウス': '東京都'})

    def test_census_is_delivered_with_counts_and_only_changes_after(self):
        self.write([stage('1', 'これから', '2026/11/01 ～ 2026/11/09', theater='劇場A', pref='東京都')])
        self.past([{'stage_id': '9', 'theater': '劇場A', 'pref': '東京都'},
                   {'stage_id': '10', 'theater': '劇場B', 'pref': '大阪府'},
                   {'stage_id': '11', 'theater': '劇場B', 'pref': '大阪府'}])
        self.assertEqual(self.deliver()['venue_census'], '2 venues (2 changed)')
        self.assertEqual(sorted(self.db.execute('SELECT venue,pref FROM venue_census')), [('劇場A', '東京都'), ('劇場B', '大阪府')])
        counts = self.db.execute("SELECT v FROM rec_meta WHERE k='venue_counts'").fetchone()[0]
        self.assertEqual(json.loads(counts), {'東京都': 1, '大阪府': 1})
        before = self.deliver()
        self.assertEqual(before['venue_census'], '2 venues (0 changed)')
        self.past([{'stage_id': '9', 'theater': '劇場A', 'pref': '東京都'}])       # 劇場B is gone: deleted
        self.assertEqual(self.deliver()['venue_census'], '1 venues (1 changed)')
        self.assertEqual(self.db.execute('SELECT venue FROM venue_census').fetchall(), [('劇場A',)])

    def test_census_waits_for_a_day_with_room(self):
        self.write([stage('1', 'これから', '2026/11/01 ～ 2026/11/09', theater='劇場A', pref='東京都')])
        self.past([{'stage_id': '9', 'theater': '劇場A', 'pref': '東京都'}])
        report = self.deliver(budget=12)
        self.assertTrue(report['venue_census'].startswith('skipped'))
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM venue_census').fetchone()[0], 0)
        self.assertEqual(self.deliver()['venue_census'], '1 venues (1 changed)')    # sent the next day


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
        def run(out, data, max_rows=None):
            (out / 'index.sql').write_text('SELECT 1;\n')
            (out / 'index-hashes.json').write_text(json.dumps({'rec_stage': {'1': rev}}))
            return rev, writes, out / 'index.sql', rows, self.left
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

    left = 0

    def test_a_partial_first_load_keeps_the_hashes_but_not_the_revision(self):
        self.left = 30
        r = self.deliver_index('rev1', 100, 50, D.WRITE_BUDGET)
        self.assertIn('30 rows left', r['index'])
        self.assertEqual(json.loads((self.data / D.INDEX_HASHES).read_text())['rec_stage']['1'], 'rev1')
        self.assertEqual(json.loads((self.data / D.STATE).read_text()).get('index', ''), '')
        self.left = 0
        r = self.deliver_index('rev1', 100, 20, D.WRITE_BUDGET)        # same revision, the rest
        self.assertNotEqual(r['index'], 'unchanged')
        self.assertEqual(json.loads((self.data / D.STATE).read_text())['index'], 'rev1')

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

    def test_index_only_run_gives_the_whole_budget_to_the_index(self):
        # 索引だけの手動実行（q-index-load-now）: 一覧・題名・カードは書かず、予算をまるごと索引に回す
        self.deliver()                                     # the daily run delivered the catalogue earlier
        seen = {}

        def run(out, data, max_rows=None):
            seen['max_rows'] = max_rows
            return self.fake_index('rev1', 300, 100)(out, data, max_rows)
        build_index, build_labels, build_cards = D.build_index, D.build_labels, D.build_cards
        D.build_index = run
        D.build_labels = D.build_cards = lambda *a: self.fail('labels and cards are for the daily run')
        try:
            self.write([stage('1', '題名が変わった', '2026/11/01 (日) ～ 2026/11/09 (月)')])
            r = D.build(self.data, self.out, TODAY, False, 30_000, index_only=True)
        finally:
            D.build_index, D.build_labels, D.build_cards = build_index, build_labels, build_cards
        self.assertEqual(seen['max_rows'], 30_000 // (D.INDEX_WRITES_PER_ROW + 1))
        self.assertEqual((r['changed'], r['writes']), (0, 300))
        self.assertEqual((self.out / 'catalogue.sql').read_text(), '')
        before = json.loads((self.data / D.STATE).read_text())
        D.commit(self.data, self.out)
        after = json.loads((self.data / D.STATE).read_text())
        self.assertEqual(after['rows'], before['rows'])    # the changed title waits for the daily run
        self.assertEqual(after['index'], 'rev1')


class SplitUploadTest(unittest.TestCase):
    def test_parts_keep_every_statement_in_order(self):
        # 2026-10-16 の 7009（q-index-load-now）: 大きな索引は文の切れ目で分けて送る
        d = Path(tempfile.mkdtemp())
        lines = [f"INSERT INTO t VALUES('{'あ' * (i % 7 + 1)}',{i});\n" for i in range(200)]
        lines.append("INSERT OR REPLACE INTO rec_meta VALUES('index_rev','r');\n")
        (d / 'x.sql').write_text(''.join(lines), encoding='utf-8')
        parts = D.split_upload(d / 'x.sql', 'x-upload', max_bytes=500)
        self.assertGreater(len(parts), 1)
        self.assertFalse((d / 'x.sql').exists())
        self.assertEqual([p.name for p in parts], sorted(p.name for p in parts))
        self.assertEqual(''.join(p.read_text(encoding='utf-8') for p in parts), ''.join(lines))
        self.assertTrue(all(len(p.read_bytes()) <= 500 for p in parts))
        self.assertIn('rec_meta', parts[-1].read_text(encoding='utf-8'))


class SettleTest(unittest.TestCase):
    """d1-upsert-counts: commit puts D1's own count in place of the estimate, only when every sent file has one."""
    def setUp(self):
        self.data = Path(tempfile.mkdtemp())
        self.out = self.data / 'out'
        self.out.mkdir()
        self.day = D.FT.today()
        D.FT.d1_spend(self.data, 30_000)
        (self.out / 'spent.json').write_text(json.dumps({'day': self.day, 'writes': 30_000}))
        (self.out / 'catalogue.sql').write_text('')                     # empty: not sent
        for f in ('index-upload-01.sql', 'index-upload-02.sql', 'cards-upload.sql'):
            (self.out / f).write_text('SELECT 1;\n')

    def log(self, name, n):
        (self.out / (name + '.log')).write_text(f'[{{"meta": {{"rows_written": {n}}}}}]')

    def test_every_file_counted(self):
        self.log('index-upload-01.sql', 2672)
        self.log('index-upload-02.sql', 2750)
        self.log('cards-upload.sql', 6000)
        self.assertIn('-> D1 counted 11422', D.settle(self.data, self.out))
        self.assertEqual(D.FT.d1_left(self.data), D.FT.CAPS['d1_writes_day'] - 11422)
        self.assertFalse((self.out / 'spent.json').exists())             # settled once

    def test_a_missing_count_keeps_the_estimate(self):
        self.log('index-upload-01.sql', 2672)
        (self.out / 'index-upload-02.sql.log').write_text('✘ [ERROR] Upstream service unavailable [code: 7009]')
        self.log('cards-upload.sql', 6000)
        self.assertIn('kept the estimate 30000', D.settle(self.data, self.out))
        self.assertEqual(D.FT.d1_left(self.data), D.FT.CAPS['d1_writes_day'] - 30_000)
