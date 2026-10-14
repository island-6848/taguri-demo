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


ASPECT_CODES = ['story', 'direction', 'acting', 'music', 'dance', 'design', 'price', 'venue']


def history(seed, fields_by_stage):
    rng = random.Random(seed)
    rows = []
    linked = sorted(fields_by_stage)
    for i in range(rng.randint(0, 40)):
        sid = rng.choice(linked) if rng.random() < .85 else ''
        # 詳細: a few aspects marked a trouble ("code") or good ("+code").
        aspects = [rng.choice(['', '+']) + c for c in rng.sample(ASPECT_CODES, rng.randint(1, 3))] if rng.random() < .4 else []
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
    keep = [c for c in d['ranked'] if c.get('b', 0) > 0]
    keep.sort(key=lambda c: (-c['strong'], -c['s'], c['stage_id']))
    return [(c['stage_id'], c['b'], c['strong'], c['person_parts']) for c in keep]


def got(rows):
    return [(c['stage_id'], c['b'], c['strong'], c['parts']) for c in rows]


def load_sql(index):
    con = sqlite3.connect(':memory:')
    for name in ('0003.sql', '0009.sql'):
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

    def test_index_holds_public_fields_only(self):
        raw, cands, fbs = catalogue(1)
        index = BI.build_index(UR.candidate_pool(raw, cands), fbs, APP.group_of)
        for st in index['stages'].values():
            self.assertLessEqual(set(st['entry']), set(BI.PUBLIC_KEYS) | {'url'})
            self.assertTrue(st['entry'].get('url', 'https://').startswith('https://'))
        self.assertTrue(all('オペラ' not in st['title'] for st in index['stages'].values()))
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
        for name in ('0003.sql', '0009.sql'):
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


if __name__ == '__main__':
    unittest.main()
