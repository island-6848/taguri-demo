"""The index-only computation must reproduce the Python recommender.

Synthetic catalogue (no private data). For several random histories and
weight settings, `score_from_index` over (a) the in-memory index and (b) the
generated SQL loaded into SQLite with migration 0003 must give the same stages,
order, scores, reasons and strength as `user_recommender.prepare` + the b > 0
filter and ordering of `user_recommender.finish`.
"""
import datetime
import json
import importlib.util
import random
import sqlite3
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
SCRIPT = HERE / 'scripts' / 'build_recommend_index.py'
spec = importlib.util.spec_from_file_location('build_recommend_index', SCRIPT)
BI = importlib.util.module_from_spec(spec)
spec.loader.exec_module(BI)
sys.path.insert(0, str(ROOT / 'tools' / 'taguri'))
import app as APP                                                  # noqa: E402
import user_recommender as UR                                      # noqa: E402
import recommend2 as RC                                            # noqa: E402

TODAY = datetime.date(2026, 10, 12)
PEOPLE = [f"人物{i:02d}" for i in range(30)] + ["O'Neil"]
STAFF = ['照明', '美術', '音響', '衣裳', '振付', '制作', '舞台監督']


def _fields(rng):
    cast = rng.sample(PEOPLE, rng.randint(0, 6))
    f = {'出演': '、'.join(cast)} if cast else {}
    if rng.random() < .8:
        f['脚本'] = rng.choice(PEOPLE)
    if rng.random() < .8:
        f['演出'] = rng.choice(PEOPLE)
    lines = [f"{role}：{rng.choice(PEOPLE)}" for role in rng.sample(STAFF, rng.randint(0, 4))]
    if lines:
        f['スタッフ'] = '\n'.join(lines)
    if rng.random() < .6:
        f['料金（1枚あたり）'] = rng.choice(['3,500円', '一般 7,800円 / 学生 4,000円', 'S席 12,000円', '15000円', '無料'])
    return f


def _period(rng):
    kind = rng.choice(['future', 'future', 'running', 'past', 'none'])
    d = lambda days: (TODAY + datetime.timedelta(days=days)).strftime('%Y/%m/%d')
    if kind == 'future':
        s = rng.randint(1, 90)
        return f"{d(s)}~{d(s + rng.randint(0, 20))}"
    if kind == 'running':
        return f"{d(-rng.randint(1, 10))}~{d(rng.randint(0, 10))}"
    if kind == 'past':
        return f"{d(-60)}~{d(-rng.randint(1, 30))}"
    return ''


def catalogue(seed):
    rng = random.Random(seed)
    cands = []
    for i in range(80):
        title = rng.choice(['舞台', '【再演】新作', 'オペラ・ガラ', '朗読劇『夜の声』', '夜舞台']) + str(i)
        cands.append({'stage_id': str(1000 + i), 'title': title, 'group': rng.choice(['劇団甲', '劇団乙', '']),
                      'theater': '劇場', 'pref': '東京都', 'period': _period(rng),
                      'url': rng.choice(['https://example.com/x', 'javascript:alert(1)', '']),
                      'fields': _fields(rng), 'why_b': ['owner reason'], '_notes': {'x': 'private'}})
    # Tours: the same production at other venues (same title, producer and
    # credits, listed in another order), with their own run dates.
    for i in range(0, 80, 7):
        src = cands[i]
        f = dict(reversed(list(src['fields'].items())))
        cands.append(dict(src, stage_id=str(1100 + i), theater='大阪の劇場', period=_period(rng), fields=f))
    # Saved bundles add a tour stage that is not in the source files.
    raw = {'ranked': [dict(cands[0], tours=[{'stage_id': '9001', 'theater': '大阪の劇場',
                                             'period': cands[0]['period']}])]}
    past = {str(2000 + i): _fields(rng) for i in range(60)}
    fields_by_stage = dict(past, **{c['stage_id']: c['fields'] for c in cands if c['fields']})
    return raw, cands, fields_by_stage


def verdict(rng, seed):
    """◎○△× (a 4-level scale), and for odd seeds also ratings on scales the
    user chose ("value/levels", 2–11 levels), as after a change of scale."""
    if seed % 2 and rng.random() < .4:
        levels = rng.choice([2, 5, 5, 11])
        return f"{rng.randint(1, levels)}/{levels}"
    return rng.choice(['◎', '◎', '○', '△', '×', ''])


THEME_POOL = ['家族', '戦争', '恋愛', '記憶', '東京の下町', '旅', '海', '父と娘']


def themes_for(seed, cands):
    """Subject words (#題材) for some candidate stages, as build_index takes them."""
    rng = random.Random(f'themes:{seed}')
    return {c['stage_id']: rng.sample(THEME_POOL, rng.randint(1, 3)) for c in cands if rng.random() < .5}


ASPECT_CODES = ['story', 'direction', 'acting', 'music', 'dance', 'design', 'price', 'venue']


def history(seed, fields_by_stage):
    rng = random.Random(seed)
    rows = []
    linked = sorted(fields_by_stage)
    for i in range(rng.randint(0, 40)):
        sid = rng.choice(linked) if rng.random() < .85 else ''
        # 詳細: a few aspects marked on 5 levels ("--code" .. "++code", 起案者の指示 2026-10-18 で 5 段階) or
        # not in this production ("~code").
        aspects = [rng.choice(['', '+', '--', '++', '~']) + c for c in rng.sample(ASPECT_CODES, rng.randint(1, 3))] if rng.random() < .4 else []
        rows.append({'key': f'w{i}', 'stage_id': sid, 'aspects': aspects,
                     'verdict': verdict(rng, seed),
                     'date': f'2026-0{rng.randint(1, 9)}-1{rng.randint(0, 9)}',
                     'updated_at': f'2026-09-{rng.randint(10, 28)} 10:00:00'})
    return rows


def with_people(rows, people):
    """What the Worker does: people of a linked record come from rec_people."""
    return [dict(r, people=[tuple(p) for p in people.get(r['stage_id'], [])]) for r in rows]


def expected(raw, cands, rated, multipliers):
    d = UR.prepare(raw, cands, rated, multipliers=multipliers, role_group=APP.group_of, today=TODAY)
    # The rule of UR.finish: score above 0 and a reason (a raising person or kind of show).
    keep = [c for c in d['ranked'] if c.get('b', 0) > 0 and UR.has_reason(c['person_parts'], c['why_kind'])]
    keep.sort(key=lambda c: (-c['strong'], -c['s'], c['stage_id']))
    return [(c['stage_id'], c['b'], c['strong'], c['person_parts']) for c in keep]


def got(rows):
    return [(c['stage_id'], c['b'], c['strong'], c['parts']) for c in rows]


def load_sql(index):
    con = sqlite3.connect(':memory:')
    for name in ('0003.sql', '0009.sql', '0016.sql', '0039.sql', '0040.sql'):
        con.executescript((HERE / 'migrations' / name).read_text())
    ver = BI.version_of(index)
    for stmt in BI.to_sql(index, ver):
        con.execute(stmt)
    return con, ver


class ParityTest(unittest.TestCase):
    def test_index_reproduces_python_recommender(self):
        weights = [{}, {'cast': 2.0, 'craft': 0.0}, {'author': 4.0, 'cast': 0.5, 'produce': 0.0}]
        compared = nonempty = 0
        for seed in range(12):
            raw, cands, fbs = catalogue(seed)
            index = BI.build_index(UR.candidate_pool(raw, cands), fbs, APP.group_of)
            con, ver = load_sql(index)
            self.addCleanup(con.close)
            for hseed in range(4):
                rated = with_people(history(seed * 100 + hseed, fbs), index['people'])
                for mult in weights:
                    want = expected(raw, cands, rated, mult)
                    mem = BI.score_from_index(*BI.memory_access(index), rated,
                                              multipliers=mult, today=TODAY)
                    sql = BI.score_from_index(*BI.sql_access(con, ver), rated,
                                              multipliers=mult, today=TODAY)
                    self.assertEqual(got(mem), want, (seed, hseed, mult))
                    self.assertEqual(got(sql), want, (seed, hseed, mult))
                    compared += 1
                    nonempty += bool(want)
        # The comparison must not pass vacuously.
        self.assertGreater(nonempty, compared // 2)

    def test_tours_group_as_the_python_screen_does(self):
        """collapse_ranked on the index == UR.collapse_tours on prepare's ranking."""
        grouped = 0
        for seed in range(12):
            raw, cands, fbs = catalogue(seed)
            index = BI.build_index(UR.candidate_pool(raw, cands), fbs, APP.group_of)
            for hseed in range(2):
                rated = with_people(history(seed * 100 + hseed, fbs), index['people'])
                d = UR.prepare(raw, cands, rated, multipliers={}, role_group=APP.group_of, today=TODAY)
                keep = [dict(c, tours=[]) for c in d['ranked'] if c.get('b', 0) > 0 and UR.has_reason(c['person_parts'], c['why_kind'])]
                keep.sort(key=lambda c: (-c['strong'], -c['s'], c['stage_id']))
                want = [(c['stage_id'], [t['stage_id'] for t in c['tours']]) for c in UR.collapse_tours(keep)]
                mem = BI.score_from_index(*BI.memory_access(index), rated, multipliers={}, today=TODAY)
                got_ = [(g['stage_id'], g['tours']) for g in BI.collapse_ranked(mem, 10 ** 6)]
                self.assertEqual(got_, want, (seed, hseed))
                grouped += sum(bool(t) for _, t in got_)
        self.assertGreater(grouped, 10, 'the catalogue must contain tours that rank')

    def test_index_holds_public_fields_only(self):
        raw, cands, fbs = catalogue(1)
        index = BI.build_index(UR.candidate_pool(raw, cands), fbs, APP.group_of)
        for st in index['stages'].values():
            self.assertLessEqual(set(st['entry']), set(BI.PUBLIC_KEYS) | {'url'})
            self.assertTrue(st['entry'].get('url', 'https://').startswith('https://'))
        # オペラ・能・歌舞伎・落語などもおすすめの候補に入れる（起案者の指示 2026-10-19「おすすめから除外しないで」）。
        # 外すのはコンサートなど舞台の上演でない催しだけ（recommend.NOT_STAGE_TITLE）
        self.assertTrue(any('オペラ' in st['title'] for st in index['stages'].values()))
        self.assertTrue(all(not any(w in st['title'] for w in RC.NOT_STAGE_TITLE) for st in index['stages'].values()))
        self.assertIn('9001', index['stages'])           # tour stage from saved bundles

    def test_version_switch_and_cleanup(self):
        raw, cands, fbs = catalogue(2)
        old = BI.build_index(UR.candidate_pool(raw, cands), fbs, APP.group_of)
        con, v1 = load_sql(old)
        self.addCleanup(con.close)
        new = BI.build_index(UR.candidate_pool(raw, cands[:40]), fbs, APP.group_of)
        v2 = BI.version_of(new)
        self.assertNotEqual(v1, v2)
        for stmt in BI.to_sql(new, v2):
            con.execute(stmt)
        self.assertEqual(con.execute("SELECT v FROM rec_meta WHERE k='current'").fetchone()[0], v2)
        for t in BI.TABLES:
            self.assertEqual(con.execute(f"SELECT count(*) FROM {t} WHERE ver<>?", (v2,)).fetchone()[0], 0)
        self.assertEqual(con.execute("SELECT count(*) FROM rec_stage").fetchone()[0], len(new['stages']))

    def test_statements_fit_d1_limit(self):
        raw, cands, fbs = catalogue(3)
        index = BI.build_index(UR.candidate_pool(raw, cands), fbs, APP.group_of)
        old = BI.MAX_STATEMENT_BYTES
        BI.MAX_STATEMENT_BYTES = 2000            # force splitting on small data
        try:
            stmts = BI.to_sql(index, 'v')
        finally:
            BI.MAX_STATEMENT_BYTES = old
        self.assertTrue(all(len(s.encode()) < 100_000 for s in stmts))
        con = sqlite3.connect(':memory:')
        self.addCleanup(con.close)
        for name in ('0003.sql', '0009.sql', '0016.sql', '0039.sql', '0040.sql'):
            con.executescript((HERE / 'migrations' / name).read_text())
        for s in stmts:
            con.execute(s)
        self.assertEqual(con.execute("SELECT count(*) FROM rec_credit").fetchone()[0],
                         len(set(index['postings'])))


# '舞台' starts some titles and is inside others of the same length (夜舞台1, 舞台12).
SEARCHES = ['舞台', '舞台1', '新作', '再演', '朗読劇夜', '『夜の声』', '夜舞台', 'ＯＮＥＩＬ', '台1',
            'x', '', '存在しない題名', '1']


def search_dates(index):
    starts = sorted({st['start'] for st in index['stages'].values() if st['start']})
    return [''] + starts[::max(len(starts) // 3, 1)]


class DiffDeliveryTest(unittest.TestCase):
    """差分で入れる（q-index-incremental）: 差分を順に当てた表は、毎回まるごと入れた表と同じ中身になる。"""

    def tables(self, con, ver):
        return {t: sorted(con.execute(f"SELECT * FROM {t} WHERE ver=?", (ver,)).fetchall()) for t in BI.TABLES}

    def full(self, index):
        con, ver = load_sql(index)
        self.addCleanup(con.close)
        return {t: sorted(tuple(BI.LIVE if i == 0 else v for i, v in enumerate(r)) for r in rows)
                for t, rows in self.tables(con, ver).items()}

    def test_diffs_reach_the_same_tables_and_write_only_what_changed(self):
        raw, cands, fbs = catalogue(3)
        a = BI.build_index(UR.candidate_pool(raw, cands), fbs, APP.group_of)
        b = BI.build_index(UR.candidate_pool(raw, cands[:40]), fbs, APP.group_of)      # stages gone
        con = sqlite3.connect(':memory:')
        self.addCleanup(con.close)
        for name in ('0003.sql', '0009.sql', '0016.sql', '0039.sql', '0040.sql'):
            con.executescript((HERE / 'migrations' / name).read_text())
        # An older versioned delivery is cleaned up by the first diff.
        for stmt in BI.to_sql(a, 'old'):
            con.execute(stmt)
        stmts, h1, c1 = BI.diff_sql(a, {})
        for stmt in stmts:
            con.execute(stmt)
        self.assertEqual(self.tables(con, BI.LIVE), self.full(a))
        self.assertEqual(con.execute("SELECT count(*) FROM rec_stage WHERE ver<>?", (BI.LIVE,)).fetchone()[0], 0)
        self.assertEqual(con.execute("SELECT v FROM rec_meta WHERE k='current'").fetchone()[0], BI.LIVE)
        self.assertEqual(con.execute("SELECT v FROM rec_meta WHERE k='index_rev'").fetchone()[0], BI.version_of(a))
        # Nothing changed: nothing but the meta rows is written.
        same, _h, c0 = BI.diff_sql(a, h1)
        self.assertEqual((c0['upserted'], c0['deleted']), (0, 0))
        self.assertFalse(any(s.startswith(('INSERT INTO rec_stage', 'INSERT INTO rec_credit', 'INSERT INTO rec_people', 'INSERT INTO rec_gram')) for s in same))
        # Fewer stages: only deletions and the rows that changed, and the tables match a full load of b.
        stmts, h2, c2 = BI.diff_sql(b, h1)
        for stmt in stmts:
            con.execute(stmt)
        self.assertEqual(self.tables(con, BI.LIVE), self.full(b))
        self.assertGreater(c2['deleted'], 0)
        self.assertLess(c2['upserted'], c1['upserted'] / 2)
        # Back again: the deleted rows come back.
        stmts, _h3, _c3 = BI.diff_sql(a, h2)
        for stmt in stmts:
            con.execute(stmt)
        self.assertEqual(self.tables(con, BI.LIVE), self.full(a))


class FirstLoadInPartsTest(DiffDeliveryTest):
    """索引の初回を何日かに分けて入れる（q-index-first-load）: 上限ずつ当てていくと、まるごと入れた表に着く。"""

    def test_parts_reach_the_full_tables_whole_stages_soonest_first(self):
        raw, cands, fbs = catalogue(4)
        a = BI.build_index(UR.candidate_pool(raw, cands), fbs, APP.group_of)
        con = sqlite3.connect(':memory:')
        self.addCleanup(con.close)
        for name in ('0003.sql', '0009.sql', '0016.sql', '0039.sql', '0040.sql'):
            con.executescript((HERE / 'migrations' / name).read_text())
        total = BI.diff_sql(a, {})[2]['upserted']
        limit = total // 4
        hashes, days, first = {}, 0, None
        while True:
            stmts, hashes, c = BI.diff_sql(a, hashes, None, limit)
            for stmt in stmts:
                con.execute(stmt)
            days += 1
            self.assertLessEqual(c['upserted'] + c['deleted'], limit)
            if first is None:
                first = c
                # Whole stages: every stage that has its rec_stage row also has its rec_people row.
                got = {r[0] for r in con.execute("SELECT stage_id FROM rec_stage")}
                self.assertTrue(got)
                for sid in got:
                    want = sorted(tuple(p[:2]) for p in set(a['postings']) if p[2] == sid)
                    have = sorted(con.execute("SELECT role, person FROM rec_credit WHERE stage_id=?", (sid,)).fetchall())
                    self.assertEqual(have, want, sid)
                rev = con.execute("SELECT v FROM rec_meta WHERE k='index_rev'").fetchone()[0]
                self.assertIn('-left', rev)
            if not c['left']:
                break
            self.assertLess(days, 10)
        self.assertGreater(days, 1)
        self.assertEqual(self.tables(con, BI.LIVE), self.full(a))
        self.assertEqual(con.execute("SELECT v FROM rec_meta WHERE k='index_rev'").fetchone()[0], BI.version_of(a))
        # Soonest stages went first.
        starts = {sid: s.get('start') or '9999' for sid, s in a['stages'].items()}
        stmts1, _h, _c = BI.diff_sql(a, {}, None, limit)
        con2 = sqlite3.connect(':memory:')
        self.addCleanup(con2.close)
        for name in ('0003.sql', '0009.sql', '0016.sql', '0039.sql', '0040.sql'):
            con2.executescript((HERE / 'migrations' / name).read_text())
        for stmt in stmts1:
            con2.execute(stmt)
        sent = {r[0] for r in con2.execute("SELECT stage_id FROM rec_stage")}
        unsent = set(a['stages']) - sent
        if unsent:
            self.assertLessEqual(max(starts[s] for s in sent), max(starts[s] for s in unsent))


class SearchTest(unittest.TestCase):
    def test_sql_search_equals_reference(self):
        found = 0
        for seed in range(12):
            raw, cands, fbs = catalogue(seed)
            index = BI.build_index(UR.candidate_pool(raw, cands), fbs, APP.group_of)
            con, ver = load_sql(index)
            self.addCleanup(con.close)
            for q in SEARCHES:
                for date in search_dates(index):
                    mem = BI.search_index(BI.memory_search(index), q, date)
                    self.assertEqual(BI.search_index(BI.sql_search(con, ver), q, date), mem, (seed, q, date))
                    found += bool(mem)
        self.assertGreater(found, 100)

    def test_search_finds_every_containing_title_in_order(self):
        raw, cands, fbs = catalogue(4)
        index = BI.build_index(UR.candidate_pool(raw, cands), fbs, APP.group_of)
        k = BI.M.R.title_key('舞台')
        want = sorted((sid for sid, st in index['stages'].items() if k in st['tkey']),
                      key=lambda sid: (index['stages'][sid]['tkey'] != k,
                                       not index['stages'][sid]['tkey'].startswith(k),
                                       len(index['stages'][sid]['tkey']), sid))
        self.assertGreater(len(want), 2)
        self.assertEqual(BI.search_index(BI.memory_search(index), '舞台', limit=100), want)
        # The record's date brings the stage running on that day to the top.
        target = [sid for sid in want[1:] if index['stages'][sid]['start']][-1]
        day = index['stages'][target]['start']
        got = BI.search_index(BI.memory_search(index), '舞台', day, limit=100)
        running = lambda sid: index['stages'][sid]['start'] and index['stages'][sid]['start'] <= day \
            and (not index['stages'][sid]['end'] or day <= index['stages'][sid]['end'])
        self.assertEqual(got, sorted(want, key=lambda sid: not running(sid)))
        self.assertLess(got.index(target), want.index(target))
        self.assertEqual(BI.search_index(BI.memory_search(index), '台'), [])

    def test_long_gram_lists_are_split(self):
        raw, cands, fbs = catalogue(5)
        index = BI.build_index(UR.candidate_pool(raw, cands), fbs, APP.group_of)
        old = BI.GRAM_PART
        BI.GRAM_PART = 3
        try:
            con, ver = load_sql(index)
            self.addCleanup(con.close)
            self.assertGreater(con.execute("SELECT max(part) FROM rec_gram").fetchone()[0], 0)
            for q in SEARCHES:
                self.assertEqual(BI.search_index(BI.sql_search(con, ver), q),
                                 BI.search_index(BI.memory_search(index), q), q)
        finally:
            BI.GRAM_PART = old


class FavouriteSeedKindsTest(unittest.TestCase):
    """Troupes / producers and works as favourites (q-favourites-seed)."""

    def setUp(self):
        raw, cands, fbs = catalogue(4)
        self.themes = themes_for(4, cands)
        self.index = BI.build_index(UR.candidate_pool(raw, cands), fbs, APP.group_of, themes=self.themes)

    def seeds(self, favs):
        seeds, _ = BI.seeds_from_favourites(BI.memory_access(self.index)[0], BI.memory_people(self.index),
                                            favs, BI.memory_matching(self.index))
        return {s['stage_id'] for s in seeds}

    def test_troupe_matches_the_producing_company_written_any_way(self):
        got = self.seeds([{'name': '劇団　甲', 'kind': '団体'}])
        self.assertTrue(got)
        self.assertTrue(all(self.index['stages'][sid]['grp'] == '劇団甲' for sid in got))
        self.assertEqual(got, self.seeds([{'name': '劇団甲', 'kind': '主催'}]))

    def test_work_matches_the_title(self):
        got = self.seeds([{'name': '『夜の声』', 'kind': '作品'}])
        self.assertTrue(got)
        self.assertTrue(all('夜の声' in self.index['stages'][sid]['title'] for sid in got))

    def test_subject_matches_words_both_ways(self):
        inside = self.seeds([{'name': '下町', 'kind': '題材'}])           # in "東京の下町"
        self.assertTrue(inside)
        self.assertTrue(all('東京の下町' in self.themes[sid] for sid in inside))
        around = self.seeds([{'name': '家族の記憶', 'kind': '題材'}])     # contains "家族", "記憶"
        self.assertTrue(around)
        self.assertTrue(all({'家族', '記憶'} & set(self.themes[sid]) for sid in around))

    def test_subject_words_are_kind_tags(self):
        sid = next(iter(sorted(self.themes)))
        tags = {(r[0], r[1]) for r in self.index['postings'] if r[2] == sid and r[0] == '#題材'}
        self.assertEqual(tags, {('#題材', w) for w in self.themes[sid]})
        self.assertTrue(all(r[4] == 'theme' for r in self.index['postings'] if r[0] == '#題材'))

    def test_theme_words_from_synopsis_elements(self):
        row = {'elements': [{'word': 'Ｗａｒ'}, {'word': '海'}, {'word': '家族'}, {'word': '家族'}]
               + [{'word': f'語{i}{i}'} for i in range(9)]}
        words = BI.theme_words(row)
        self.assertEqual(words[:2], ['war', '家族'])                     # normalised, 1 letter dropped, no repeats
        self.assertEqual(len(words), 11)
        many = {'elements': [{'word': f'語{i}{i}'} for i in range(20)]}
        self.assertEqual(len(BI.theme_words(many)), BI.MAX_THEME_WORDS)

    def test_theme_terms_cap_and_weigh_each_kind(self):
        # 起案者の判断（2026-10-18）「6＋2 に組み替えて」: 種類ごとの上限と重さ、根拠の強さ
        row = {'elements': [{'kind': '題材', 'word': f'題材{i}'} for i in range(6)]
               + [{'kind': 'モチーフ', 'word': '閉店間際の銭湯'},
                  {'kind': '舞台設定', 'word': '江戸'},
                  {'kind': '語り口', 'word': '群像劇', 'basis': '推定', 'from': '…'},
                  {'kind': 'テーマ', 'word': 'すれ違い', 'basis': '作風', 'from': '…'},
                  {'kind': '味わい', 'word': 'アングラ', 'basis': '定評', 'from': '…'}]}
        terms = dict(BI.theme_terms(row))
        self.assertEqual(sum(1 for w in terms if w.startswith('題材')), 4, '題材は 4 つまで')
        self.assertNotIn('閉店間際の銭湯', terms, 'モチーフは索引に入れない')
        self.assertEqual(terms['題材0'], 1.0)
        self.assertEqual(terms['江戸'], 0.5)
        self.assertEqual(terms['群像劇'], 0.49)                        # 語り口 0.7 × 推定 0.7
        self.assertEqual(terms['すれ違い'], 0.5)                       # テーマ 1.0 × 作風 0.5
        self.assertEqual(terms['アングラ'], 0.3)                       # 味わい 1.0 × 定評 0.3
        pool = UR.candidate_pool({}, [{'stage_id': '9', 'title': '公演', 'period': '2099/01/01 〜 2099/01/02', 'fields': {}}])
        index = BI.build_index(pool, {}, APP.group_of, themes={'9': BI.theme_terms(row)})
        w = {r[1]: r[3] for r in index['postings'] if r[0] == '#題材' and r[2] == '9'}
        self.assertEqual(w['江戸'], round(UR.GENRE_W * 0.5, 6))

    def test_too_short_or_unknown_names_add_nothing(self):
        self.assertEqual(self.seeds([{'name': '劇', 'kind': '団体'}, {'name': '海', 'kind': '題材'}]), set())


class OnboardingTest(unittest.TestCase):
    """onboarding_list: stages already on, covering the coming catalogue."""

    def index(self):
        st = lambda start: {"start": start}
        return {"stages": {"p1": st("2026-09-01"), "p2": st("2026-09-02"), "p3": st("2026-09-03"),
                           "c1": st("2026-11-01"), "c2": st("2026-11-02"), "c3": st("2026-12-01")},
                "postings": [("出演", "甲", "c1", 1.0, "cast"), ("出演", "甲", "c2", 1.0, "cast"),
                             ("出演", "乙", "c3", 1.0, "cast"), ("#形式", "朗読", "c3", 1.0, "theme"),
                             ("出演", "甲", "p1", 1.0, "cast"), ("出演", "甲", "p2", 1.0, "cast"),
                             ("出演", "乙", "p2", 1.0, "cast"), ("出演", "丙", "p3", 1.0, "cast")]}

    def test_greedy_cover_of_coming_stages(self):
        # p2 covers 甲 (2 coming) and 乙 (1); p1 then adds nothing new; p3 nothing.
        self.assertEqual(BI.onboarding_list(self.index(), TODAY), ["p2"])

    def test_only_stages_already_on_are_asked(self):
        out = BI.onboarding_list(self.index(), datetime.date(2026, 11, 1))
        self.assertNotIn("c2", out)
        self.assertNotIn("c3", out)

    def test_written_with_its_version(self):
        raw, cands, fbs = catalogue(0)
        index = BI.build_index(UR.candidate_pool(raw, cands), fbs, APP.group_of)
        ver = BI.version_of(index)
        ids = BI.onboarding_list(index, TODAY)
        self.assertTrue(ids)
        con = sqlite3.connect(":memory:")
        for f in sorted((HERE / "migrations").glob("*.sql")):
            con.executescript(f.read_text())
        for stmt in BI.to_sql(index, ver, ids):
            con.execute(stmt)
        v = json.loads(con.execute("SELECT v FROM rec_meta WHERE k='onboarding'").fetchone()[0])
        self.assertEqual(v, {"ver": ver, "ids": ids})


class AffiliationTest(unittest.TestCase):
    """所属の表 rec_affil（起案者の指示 2026-10-19「所属の表をつくって」、dec-affiliation-table）。"""

    def test_rows_per_stage_with_kind_from_past_and_coming_stages(self):
        pool = {'1': {'title': '甲', 'period': '2026/11/01 〜 2026/11/03', 'group': '劇団丙',
                      'fields': {'出演': '山田太郎（劇団丙）、佐藤花子（丁プロダクション）'}}}
        past = [{'stage_id': '2', 'start': '2025-05-01', 'group': '戊企画',
                 'fields': {'出演': '山田太郎（劇団己）、鈴木一（Wキャスト）、高橋二（佐藤花子）、伊藤三（無名の会合）'}}]
        index = BI.build_index(pool, {}, APP.group_of, past=past)
        self.assertEqual(index['affil'], [
            ('丁プロダクション', '佐藤花子', '1', '2026-11-01', '事務所', '丁プロダクション'),
            ('劇団丙', '山田太郎', '1', '2026-11-01', '劇団', '劇団丙'),
            ('劇団己', '山田太郎', '2', '2025-05-01', '劇団', '劇団己'),
            ('無名の会合', '伊藤三', '2', '2025-05-01', '', '無名の会合'),
        ])

    def test_ways_of_writing_one_affiliation_are_one(self):
        pool = {str(i): {'title': f'題{i}', 'period': f'2026/11/0{i} 〜 2026/11/0{i}', 'fields': {'出演': c}}
                for i, c in enumerate(['甲野一（劇団青年座）、乙野二（流山児★事務所）', '丙野三（青年座）、丁野四（流山児☆事務所）',
                                       '戊野五（青年座）、己野六（株式会社流山児★事務所）', '庚野七（EXILE）、辛野八（劇団EXILE）、壬野九（流山児★事務所）'], 1)}
        rows = BI.build_index(pool, {}, APP.group_of)['affil']
        self.assertEqual({(r[0], r[5]) for r in rows}, {
            ('青年座', '劇団青年座'), ('青年座', '青年座'),
            ('流山児★事務所', '流山児★事務所'), ('流山児★事務所', '流山児☆事務所'), ('流山児★事務所', '株式会社流山児★事務所'),
            ('EXILE', 'EXILE'), ('劇団EXILE', '劇団EXILE')})
        # 束ねた所属の種類は、束のどれかに付いたもの（「劇団青年座」が劇団なので「青年座」の行も劇団）
        self.assertEqual({r[4] for r in rows if r[0] == '青年座'}, {'劇団'})

    def test_delivered_with_the_index_and_only_changes_next_time(self):
        pool = {'1': {'title': '甲', 'period': '2026/11/01 〜 2026/11/03', 'fields': {'出演': '山田太郎（劇団丙）'}}}
        index = BI.build_index(pool, {}, APP.group_of)
        con = sqlite3.connect(':memory:')
        for name in ('0003.sql', '0009.sql', '0016.sql', '0039.sql', '0040.sql'):
            con.executescript((HERE / 'migrations' / name).read_text())
        stmts, hashes, _ = BI.diff_sql(index, {})
        for st in stmts:
            con.execute(st)
        self.assertEqual(con.execute('SELECT affil, person, stage_id FROM rec_affil').fetchall(), [('劇団丙', '山田太郎', '1')])
        again, _, counts = BI.diff_sql(index, hashes)
        self.assertFalse(any(s.startswith('INSERT INTO rec_affil') for s in again))


if __name__ == '__main__':
    unittest.main()
