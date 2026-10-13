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
            cases.append({'rated': rated, 'multipliers': mult, 'expected': expected})
    out['catalogues'].append({'seed': seed, 'ver': ver, 'sql': BI.to_sql(index, ver), 'cases': cases})
json.dump(out, sys.stdout, ensure_ascii=False)
