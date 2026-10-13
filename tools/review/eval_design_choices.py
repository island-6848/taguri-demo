#!/usr/bin/env python3
"""Check each design choice of person-graded-v2 against alternatives, on
public data, choosing on one group of users and confirming on another.

    python3 tools/review/eval_design_choices.py --data DIR --types FILE [--seed 1]

Choices compared (one at a time from the current setting, then the best
combination is confirmed on held-out users):
- grade:  how a rating becomes a number
    equal_z     ◎○△× = 4/3/2/1 (equal steps), then (x − mean) / spread  [current]
    percentile  the rating's mid-rank among the user's own ratings, − 0.5
                (no equal-step assumption; ordinal, per user)
    top_only    1 for the user's top grade, 0 otherwise, then centred (v1-like)
- agg:    a person's value from the movies they were in
    mean        Σ / (n + k)  [current]     sum   Σ (no averaging)
- k:      how much few movies are discounted (0, 1, 3, 5, 10; current 3)
- dir_w:  director weight relative to actors (0.2, 0.4, 1.0; current 0.4)
- top:    how many of a movie's people are added (1, 3, 5, all; current 3
          positive + 3 negative)
- genre:  weight of the user's own genre preference added to the score
          (0, 0.5, 1, 2; current 0)

Protocol as eval_person_reco.learning_curve: per user, 3 random orders, the
last 40 ratings fixed for checking, the method sees the first k ratings only
(k = 10, 40, 80). Tuning users and checking users are disjoint. Two measures:
- auc_top: the user's top-grade movies ranked above the rest (favours methods
  that only look at the top grade)
- pairs: every pair of checked movies the user rated differently, ranked in
  the user's order (counts △ above × as well; ties count half)
Choices are picked on the mean of both measures.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import random
import statistics
from collections import defaultdict
from pathlib import Path

spec = importlib.util.spec_from_file_location("E", Path(__file__).with_name("eval_person_reco.py"))
E = importlib.util.module_from_spec(spec)
spec.loader.exec_module(E)

KS = (10, 40, 80)
TEST_SIZE = 40
CURRENT = {"grade": "equal_z", "agg": "mean", "k": 3, "dir_w": 0.4, "top": 3, "genre": 0.0}
GRID = {"grade": ["equal_z", "percentile", "top_only"], "agg": ["mean", "sum"],
        "k": [0, 1, 3, 5, 10], "dir_w": [0.2, 0.4, 1.0], "top": [1, 3, 5, None],
        "genre": [0.0, 0.5, 1.0, 2.0]}


def load_types(path: Path) -> dict:
    types = defaultdict(list)
    for line in path.read_text().split("\n"):
        if line.strip():
            m, t, *_ = line.split()
            types[m].append(t)
    return types


def values(history, p):
    """Rating -> number, per the 'grade' choice."""
    rs = [r for _, r in history]
    n = len(rs)
    if p["grade"] == "percentile":
        def x(r):
            below = sum(v < r for v in rs)
            same = sum(v == r for v in rs)
            return (below + 0.5 * same) / n - 0.5
        return [(m, x(r)) for m, r in history]
    if p["grade"] == "top_only":
        top = max(rs)
        raw = [(m, float(r == top)) for m, r in history]
    else:
        raw = [(m, float(r)) for m, r in history]
    vals = [v for _, v in raw]
    mean = statistics.fmean(vals)
    sd = statistics.pstdev(vals) if n > 1 else 0.0
    sd = sd or 1.0
    return [(m, (v - mean) / sd) for m, v in raw]


def scorer(history, people, types, p):
    roles = {"actor": 1.0, "director": p["dir_w"]}
    acc, gacc = defaultdict(lambda: [0, 0.0]), defaultdict(lambda: [0, 0.0])
    for m, x in values(history, p):
        for rp in set(people.get(m, ())):
            acc[rp][0] += 1
            acc[rp][1] += x
        for t in set(types.get(m, ())):
            gacc[t][0] += 1
            gacc[t][1] += x
    def person_value(n, s):
        return s if p["agg"] == "sum" else s / (n + p["k"])
    def score(m):
        parts = [person_value(*acc[(role, q)]) * roles[role]
                 for role, q in set(people.get(m, ())) if (role, q) in acc]
        pos = sorted((v for v in parts if v > 0), reverse=True)
        neg = sorted(v for v in parts if v < 0)
        if p["top"] is not None:
            pos, neg = pos[:p["top"]], neg[:p["top"]]
        s = sum(pos) + sum(neg)
        g = [gacc[t][1] / (gacc[t][0] + 3) for t in set(types.get(m, ())) if t in gacc]
        if p["genre"] and g:
            s += p["genre"] * statistics.fmean(g)
        return s if (parts or g) else None
    return score


def pair_accuracy(score, test):
    """Share of differently rated pairs ordered as the user rated them."""
    sc = {m: (score(m) or 0.0) for m, _ in test}
    good = total = 0.0
    for i, (m1, r1) in enumerate(test):
        for m2, r2 in test[i + 1:]:
            if r1 == r2:
                continue
            total += 1
            a, b = (sc[m1], sc[m2]) if r1 > r2 else (sc[m2], sc[m1])
            good += 1.0 if a > b else 0.5 if a == b else 0.0
    return good / total if total else None


def evaluate(params, users, ratings, people, types, seed, shuffles=3):
    """Per k: mean over users of (auc_top + pairs) / 2, and of each measure."""
    per = {k: [] for k in KS}
    per_user = {k: {} for k in KS}
    parts = {k: {"auc_top": [], "pairs": []} for k in KS}
    for u in users:
        items = sorted(ratings[u].items())
        got = {k: [] for k in KS}
        got_a = {k: [] for k in KS}
        got_p = {k: [] for k in KS}
        for s in range(shuffles):
            rng = random.Random(f"dc:{seed}:{u}:{s}")
            order = items[:]
            rng.shuffle(order)
            test, train = order[-TEST_SIZE:], order[:-TEST_SIZE]
            for k in KS:
                f = scorer(train[:k], people, types, params)
                r = E.evaluate_one(f, test, random.Random(f"dc:{seed}:{u}:{s}:t"))
                pa = pair_accuracy(f, test)
                if r["auc_top"] is not None and pa is not None:
                    got[k].append((r["auc_top"] + pa) / 2)
                    got_a[k].append(r["auc_top"])
                    got_p[k].append(pa)
        for k in KS:
            if got[k]:
                per_user[k][u] = statistics.fmean(got[k])
                per[k].append(per_user[k][u])
                parts[k]["auc_top"].append(statistics.fmean(got_a[k]))
                parts[k]["pairs"].append(statistics.fmean(got_p[k]))
    evaluate.parts = {k: {m: round(statistics.fmean(v), 4) for m, v in d.items()} for k, d in parts.items()}
    return {k: statistics.fmean(v) for k, v in per.items()}, per_user


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--types", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--tune-users", type=int, default=300)
    ap.add_argument("--test-users", type=int, default=500)
    a = ap.parse_args()
    ratings, people = E.load(a.data)
    types = load_types(a.types)
    eligible = sorted(u for u, rs in ratings.items() if len(rs) >= max(KS) + TEST_SIZE)
    rng = random.Random(a.seed)
    rng.shuffle(eligible)
    tune, test = eligible[:a.tune_users], eligible[a.tune_users:a.tune_users + a.test_users]
    out = {"tune_users": len(tune), "test_users": len(test), "one_at_a_time": {}}
    # 1. One choice at a time from the current setting (tuning users).
    best = dict(CURRENT)
    for name, options in GRID.items():
        rows = []
        for o in options:
            p = dict(CURRENT, **{name: o})
            m, _ = evaluate(p, tune, ratings, people, types, a.seed)
            rows.append({"option": o, **{f"k{k}": round(v, 4) for k, v in m.items()},
                         "detail": evaluate.parts})
        out["one_at_a_time"][name] = rows
        # Pick by the mean over k (all stages of use count).
        best[name] = max(rows, key=lambda r: statistics.fmean(r[f"k{k}"] for k in KS))["option"]
    out["chosen"] = best
    # 2. Confirm the combination on the held-out users against the current setting.
    cur_m, cur_u = evaluate(CURRENT, test, ratings, people, types, a.seed + 100)
    cur_parts = evaluate.parts
    new_m, new_u = evaluate(best, test, ratings, people, types, a.seed + 100)
    new_parts = evaluate.parts
    conf = {}
    for k in KS:
        common = [u for u in new_u[k] if u in cur_u[k]]
        d = [new_u[k][u] - cur_u[k][u] for u in common]
        conf[k] = {"current": round(cur_m[k], 4), "chosen": round(new_m[k], 4),
                   "diff": round(statistics.fmean(d), 4),
                   "ci95": round(1.96 * statistics.pstdev(d) / len(d) ** 0.5, 4),
                   "better_users": round(sum(x > 0 for x in d) / len(d), 3),
                   "current_parts": cur_parts[k], "chosen_parts": new_parts[k]}
    out["confirm_on_heldout"] = conf
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
