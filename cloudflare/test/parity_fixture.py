"""Write Python's recommendations for synthetic catalogues as JSON on stdout.

Used by test/recommend.test.js: the Worker's JS scorer must reproduce these
exactly. Same synthetic data as test_recommend_index.py (no private data).
"""
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('test_recommend_index', HERE / 'test_recommend_index.py')
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)
BI, UR, APP = T.BI, T.UR, T.APP

WEIGHTS = [{}, {'cast': 2.0, 'craft': 0.0}, {'author': 4.0, 'cast': 0.5, 'produce': 0.0}]
out = {'today': T.TODAY.isoformat(), 'catalogues': []}
for seed in range(12):
    raw, cands, fbs = T.catalogue(seed)
    index = BI.build_index(UR.candidate_pool(raw, cands), fbs, APP.group_of)
    ver = BI.version_of(index)
    cases = []
    for hseed in range(4):
        rated = T.with_people(T.history(seed * 100 + hseed, fbs), index['people'])
        for mult in WEIGHTS:
            expected = BI.score_from_index(*BI.memory_access(index), rated, multipliers=mult, today=T.TODAY)
            # What the Worker lists after the user reacts to the top stage: one
            # slot per tour (collapse_ranked), the first RECOMMEND_TOP.
            cases.append({'rated': rated, 'multipliers': mult, 'expected': expected,
                          'listed_after_first': BI.collapse_ranked(expected[1:], 15)})
    # Favourites as seeds (q-favourites-seed): with no ratings and with a history.
    cast = sorted({(p[0], p[1]) for p in index['postings'] if not p[0].startswith('#')})
    picks = [cast[(seed * 7 + i * 13) % len(cast)][1] for i in range(3)]
    favs = [{'name': picks[0], 'kind': '人'}, {'name': picks[1], 'kind': '原作者'},
            {'name': picks[2], 'kind': '団体'}, {'name': '誰でもない人', 'kind': '人'}]
    # Troupes / producers by the producing company, works by the title (some seeds only).
    if seed % 3 == 1:
        favs += [{'name': '劇団　甲', 'kind': '団体'}]
    if seed % 3 == 2:
        favs += [{'name': '『夜の声』', 'kind': '作品'}, {'name': '劇団乙', 'kind': '主催'}]
    seeds, skip = BI.seeds_from_favourites(BI.memory_access(index)[0], BI.memory_people(index), favs,
                                           BI.memory_matching(index))
    for rated in ([], T.with_people(T.history(seed * 100 + 9, fbs), index['people'])):
        expected = BI.score_from_index(*BI.memory_access(index), rated, multipliers={}, today=T.TODAY,
                                       seeds=seeds, skip=skip)
        cases.append({'rated': rated, 'multipliers': {}, 'favourites': favs, 'seeds': [s['stage_id'] for s in seeds],
                      'expected': expected, 'listed': BI.collapse_ranked(expected, 15)})
    searches = [{'q': q, 'date': d, 'expected': BI.search_index(BI.memory_search(index), q, d)}
                for q in T.SEARCHES for d in T.search_dates(index)]
    onboarding = BI.onboarding_list(index, T.TODAY)
    out['catalogues'].append({'seed': seed, 'ver': ver, 'sql': BI.to_sql(index, ver, onboarding), 'cases': cases,
                              'searches': searches, 'onboarding': onboarding})

# Title keys: the Worker normalises the query as rate_performances.title_key does.
TITLES = ['【Premium限定】ミュージカル『エリザベート』', '〈セット券〉 夏の夜の夢', '(再演)ハムレット',
          '【とても長い冠の文字が十二文字を超える】題名', '【改行\nを含む】題名', 'ＡＢＣ　ｄｅｆ', 'ΑΣ ΣΑ ΟΔΥΣΣΕΥΣ',
          'İstanbul', '\ufeffBOM付き\ufeff', '\x1c区切り\x1f', '\x85次行', '\u3000全角空白\u3000', '🎭ミュージカル🎭',
          'Ⅻ夜・十二夜', 'ﾊﾟﾘの恋人', 'Mr.&Mrs. ~smith~', "O'Neil “作品” ’26", '', '  ', '【】', '[a]b', '<<x>>y']
rng = T.random.Random(7)
POOL = list('あア亜aAＡ１1 　・『』【】〈〉()（）[]-−–—~〜/／:：!！?？\'"“”’.,。，Σσİı\ufeff\x1c\x85\u2028\n\tÅﬁ㍿')
TITLES += [''.join(rng.choice(POOL) for _ in range(rng.randint(0, 16))) for _ in range(3000)]
out['title_keys'] = [[t, BI.M.R.title_key(t)] for t in TITLES]
json.dump(out, sys.stdout, ensure_ascii=False)
