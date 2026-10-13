#!/usr/bin/env python3
"""Onboarding / preference elicitation simulation on Douban (own data only).

Which k past works should a new user be asked to rate first?  The user's pool
of rateable works = their ratings outside the fixed test 40.  Strategies pick k
of them WITHOUT looking at any rating value:
  random              : first k of the shuffled pool (= the main protocol)
  cover_catalog       : greedy, maximise new persons/genres weighted by how
                        often they appear in the whole catalogue
  cover_candidates    : greedy, weighted by how often they appear among the
                        works to be ranked (in たぐり: the public upcoming
                        catalogue; here: the user's 40 test works, credits only)
Then graded (person) and graded+genre score the test 40; AUC of top grade.

    python3 -I exp_elicit.py --here DIR --repo DIR --data DIR --extra DIR --seed 1
"""
import argparse
import json
import math
import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ap = argparse.ArgumentParser()
for x in ("--here", "--repo", "--data", "--extra", "--out"):
    ap.add_argument(x)
ap.add_argument("--seed", type=int, default=1)
ap.add_argument("--users", type=int, default=500)
a = ap.parse_args()
sys.path.insert(0, a.repo)
sys.path.insert(0, a.here)
import eval_person_reco as E  # noqa
import eval_privacy_reco as X  # noqa

ratings, people = E.load(Path(a.data))
types = X.load_types(Path(a.extra))
eligible = sorted(u for u, rs in ratings.items() if len(rs) >= 100)
users = random.Random(a.seed).sample(eligible, min(a.users, len(eligible)))
users = [u for u in users if len(ratings[u]) >= 120]
cat = Counter()
for m in set(people) | set(types):
    for rp in set(people.get(m, ())):
        cat[rp] += 1
    for g in set(types.get(m, ())):
        cat[("g", g)] += 1


def feats(m):
    return {rp for rp in people.get(m, ())} | {("g", g) for g in types.get(m, ())}


def greedy(pool, k, weight):
    chosen, seen = [], set()
    rest = list(pool)
    while len(chosen) < k and rest:
        best = max(range(len(rest)), key=lambda i: (sum(weight(f) for f in feats(rest[i][0]) - seen), -i))
        it = rest.pop(best)
        chosen.append(it)
        seen |= feats(it[0])
    return chosen


def gg(hist):
    st = X.Stats(hist, people, types)
    g = E.graded(hist, people)
    return lambda m: (g(m) or 0.0) + X.genre_part(st, m, types)[0]


METHODS = {"graded": lambda h: E.graded(h, people), "graded+genre": gg}
KS = (5, 10, 20, 40)
res = defaultdict(lambda: defaultdict(list))   # (strategy, method, k) -> user -> aucs
for u in users:
    items = sorted(ratings[u].items())
    for s in range(3):
        test, pool = X.splits(items, a.seed, u, s)
        cand = Counter()
        for m, _ in test:
            for f in feats(m):
                cand[f] += 1
        strategies = {
            "random": lambda k: pool[:k],
            "cover_catalog": lambda k: greedy(pool, k, lambda f: math.log1p(cat[f]) * (0.3 if f[0] == "g" else 1)),
            "cover_candidates": lambda k: greedy(pool, k, lambda f: cand[f] * (0.3 if f[0] == "g" else 1)),
        }
        for sn, pick in strategies.items():
            for k in KS:
                hist = pick(k)
                for mn, mk in METHODS.items():
                    r = E.evaluate_one(mk(hist), test, random.Random(f"lc:{a.seed}:{u}:{s}:t"))
                    if r["auc_top"] is not None:
                        res[(sn, mn, k)][u].append(r["auc_top"])
out = {}
for mn in METHODS:
    for k in KS:
        base = {u: statistics.fmean(v) for u, v in res[("random", mn, k)].items()}
        for sn in ("random", "cover_catalog", "cover_candidates"):
            cur = {u: statistics.fmean(v) for u, v in res[(sn, mn, k)].items()}
            us = sorted(set(cur) & set(base))
            v = [cur[u] for u in us]
            d = [cur[u] - base[u] for u in us]
            out[f"{mn}|{sn}|k={k}"] = {"auc": round(statistics.fmean(v), 4),
                                       "ci": round(1.96 * statistics.pstdev(v) / math.sqrt(len(v)), 4),
                                       "diff_vs_random": round(statistics.fmean(d), 4),
                                       "diff_ci": round(1.96 * statistics.pstdev(d) / math.sqrt(len(d)), 4),
                                       "better": round(sum(x > 0 for x in d) / len(d), 3),
                                       "worse": round(sum(x < 0 for x in d) / len(d), 3), "n": len(us)}
txt = json.dumps(out, indent=1)
if a.out:
    Path(a.out).write_text(txt)
print(txt)
