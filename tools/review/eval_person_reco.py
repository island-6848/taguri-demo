#!/usr/bin/env python3
"""Compare person-based recommenders on a public dataset, user by user.

    python3 tools/review/eval_person_reco.py --data DIR [--users 500] [--seed 1]

Why: たぐりの推薦（person-feedback-v1）を変える前に、変えた案が本当に良いかを、
持ち主 1 人（n=1）ではなく実在の多数の人の評価で確かめる。利用者の記録は集めない
方針なので、たぐりの利用者ではなく**公開データ**を使う。

Data (not in the repository; download yourself): the Douban Movie set from
librahu/HIN-Datasets-for-Recommendation-and-Network-Embedding —
user_movie.dat (user, movie, rating 1–5), movie_actor.dat, movie_director.dat.
It has no timestamps, so each user's ratings are put in a random order
(several shuffles) and treated as the order they were given.

Protocol (per user, predict-then-check): after the first k ratings of the
order, every method scores the user's remaining rated movies using only those
k ratings (no other user's data — like たぐり), and we measure how well the
ranking matches the user's own later ratings:
- auc_top: how often a movie the user gave their own highest grade is ranked
  above one they gave less (ties count half)
- ndcg10: NDCG@10 with gain = rating − 1
k runs over a learning curve (5, 10, 20, 40, 80) to see "the more you use it,
the better". Methods only rank movies they can score; unscored movies go last
as neutral (score 0), ties in a fixed random order (the same for every method).
"""
from __future__ import annotations

import argparse
import json
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path

ROLE_W = {"actor": 1.0, "director": 0.4}      # recommend2.ROLE_W: 出演 1.0, 演出 0.4
SMOOTH_A, SMOOTH_B, CONF_K, TOP_N = 1, 2, 3, 3   # measure_nets / user_recommender
KS = (5, 10, 20, 40, 80)


def load(data: Path):
    ratings = defaultdict(dict)
    for line in (data / "user_movie.dat").read_text().split("\n"):
        if line.strip():
            u, m, r = line.split()
            ratings[u][m] = int(r)
    people = defaultdict(list)
    for name, role in (("movie_actor.dat", "actor"), ("movie_director.dat", "director")):
        for line in (data / name).read_text().split("\n"):
            if line.strip():
                m, p, _ = line.split()
                people[m].append((role, p))
    return ratings, people


# ---------------------------------------------------------------- methods
# Each method: fit(history [(movie, rating)], people) -> score(movie) or None.

def b0_current(history, people, top_grade=5):
    """person-feedback-v1: only the top grade (◎) counts as liked; a person's
    smoothed ◎ rate minus the user's own ◎ rate, times confidence and role
    weight; sum of the top 3 positive parts."""
    base = sum(r >= top_grade for _, r in history) / max(len(history), 1)
    roster = defaultdict(lambda: [0, 0])
    for m, r in history:
        for rp in set(people.get(m, ())):
            roster[rp][0] += 1
            roster[rp][1] += r >= top_grade
    def score(m):
        parts = []
        for role, p in set(people.get(m, ())):
            n, o = roster.get((role, p), (0, 0))
            if not n or not o:
                continue
            c = ((o + SMOOTH_A) / (n + SMOOTH_B) - base) * n / (n + CONF_K) * ROLE_W[role]
            if c > 0:
                parts.append(c)
        if not parts:
            return None
        return sum(sorted(parts, reverse=True)[:TOP_N])
    return score


def b0_relative_top(history, people):
    """B0 with ◎ = the user's own highest grade so far (fixes strict raters)."""
    top = max((r for _, r in history), default=5)
    return b0_current(history, people, top_grade=top)


def graded(history, people, shrink=CONF_K, roles=ROLE_W, use_negative=True):
    """Use every grade, relative to this user's own habits: each rating becomes
    (rating − user mean) / user spread; a person's value is the shrunken mean
    of that over the movies they were in (n/(n+shrink)); a movie's score is the
    sum of its strongest 3 parts (negative parts lower it when use_negative)."""
    rs = [r for _, r in history]
    mean = statistics.fmean(rs) if rs else 0.0
    sd = statistics.pstdev(rs) if len(rs) > 1 else 0.0
    sd = sd if sd > 0 else 1.0
    acc = defaultdict(lambda: [0, 0.0])
    for m, r in history:
        z = (r - mean) / sd
        for rp in set(people.get(m, ())):
            acc[rp][0] += 1
            acc[rp][1] += z
    def score(m):
        parts = []
        for role, p in set(people.get(m, ())):
            if (role, p) not in acc:
                continue
            n, s = acc[(role, p)]
            parts.append(s / (n + shrink) * roles[role])      # = mean·n/(n+shrink)
        if not parts:
            return None
        pos = sorted((x for x in parts if x > 0), reverse=True)[:TOP_N]
        neg = sorted(x for x in parts if x < 0)[:TOP_N] if use_negative else []
        return sum(pos) + sum(neg)
    return score


def graded_learned_roles(history, people):
    """graded, plus per-user role weights chosen on the user's own history
    (inner split), kept only if clearly better than the default weights —
    otherwise the defaults (the safety gate)."""
    if len(history) < 20:
        return graded(history, people)
    cut = len(history) * 2 // 3
    inner_train, inner_test = history[:cut], history[cut:]
    def inner_auc(roles):
        f = graded(inner_train, people, roles=roles)
        return evaluate_one(f, inner_test, random.Random(0))["auc_top"]
    default = inner_auc(ROLE_W)
    best, best_auc = ROLE_W, default
    for d in (0.0, 0.2, 0.7, 1.0):
        roles = {"actor": 1.0, "director": d}
        a = inner_auc(roles)
        if a is not None and default is not None and a > best_auc + 0.02:
            best, best_auc = roles, a
    return graded(history, people, roles=best)


CURRENT = {}          # the user being evaluated (for the reference method only)


def reference_item_mean(sums):
    """Reference only (not allowed in たぐり: uses other users' ratings):
    rank by the movie's average rating among everyone else (the user's own
    rating left out). Shows that the protocol can detect a working signal."""
    def make(history, people):
        own = CURRENT["ratings"]
        def score(m):
            s, n = sums.get(m, (0, 0))
            s, n = s - own.get(m, 0), n - (m in own)
            return s / n - 3 if n else None
        return score
    return make


METHODS = {
    "B0_current": b0_current,
    "B0_relative_top": b0_relative_top,
    "graded": graded,
    "graded_no_negative": lambda h, p: graded(h, p, use_negative=False),
    "graded_learned_roles": graded_learned_roles,
}


# ---------------------------------------------------------------- metrics

def evaluate_one(score, test, rng):
    """Rank the test movies by score (unscored last, fixed random order)."""
    if not test:
        return {"auc_top": None, "ndcg10": None, "coverage": None, "auc_scored": None}
    order = list(test)
    rng.shuffle(order)
    tie = {m: i for i, (m, _) in enumerate(order)}
    scored = [(score(m), m, r) for m, r in order]
    # Unscored movies count as neutral (0): a method that knows nothing about a
    # movie neither raises nor lowers it.
    ranked = sorted(scored, key=lambda x: (-(x[0] or 0.0), tie[x[1]]))
    top = max(r for _, r in test)
    pos = [i for i, (_, _, r) in enumerate(ranked) if r == top]
    neg = [i for i, (_, _, r) in enumerate(ranked) if r < top]
    auc = None
    if pos and neg:
        # rank positions: smaller is better; count pairs with pos before neg
        wins = 0
        j = 0
        negs = sorted(neg)
        for i in sorted(pos):
            while j < len(negs) and negs[j] < i:
                j += 1
            wins += len(negs) - j
        auc = wins / (len(pos) * len(neg))
    # Among movies the method could score only (how good its scores are, apart
    # from how many movies it can score at all).
    sc = [(x, r) for x, _, r in scored if x is not None]
    auc_s = None
    if sc:
        ps = [x for x, r in sc if r == top]
        ns = [x for x, r in sc if r < top]
        if ps and ns:
            auc_s = sum((p > n) + 0.5 * (p == n) for p in ps for n in ns) / (len(ps) * len(ns))
    gains = [r - 1 for _, _, r in ranked]
    dcg = sum(g / math.log2(i + 2) for i, g in enumerate(gains[:10]))
    ideal = sorted(gains, reverse=True)
    idcg = sum(g / math.log2(i + 2) for i, g in enumerate(ideal[:10]))
    return {"auc_top": auc, "ndcg10": dcg / idcg if idcg else None,
            "coverage": len(sc) / len(test), "auc_scored": auc_s}


TEST_SIZE = 40


def learning_curve(ratings, people, users, seed, methods=("B0_current", "graded"), shuffles=3):
    """"The more you use it, the better", measured cleanly: per user and order,
    the last TEST_SIZE ratings are a fixed test set, and only the number of
    earlier ratings the method may use (k) changes. Returns, per method, the
    mean AUC at each k and the share of users whose AUC rose from the smallest
    to the largest k (and fell)."""
    ks = [k for k in KS]
    curves = {m: defaultdict(list) for m in methods}
    rise = {m: [] for m in methods}
    for u in users:
        CURRENT["ratings"] = ratings[u]
        items = sorted(ratings[u].items())
        if len(items) < max(ks) + TEST_SIZE:
            continue
        per = {m: defaultdict(list) for m in methods}
        for s in range(shuffles):
            rng = random.Random(f"lc:{seed}:{u}:{s}")
            order = items[:]
            rng.shuffle(order)
            test, train = order[-TEST_SIZE:], order[:-TEST_SIZE]
            for k in ks:
                for m in methods:
                    res = evaluate_one(METHODS[m](train[:k], people), test, random.Random(f"lc:{seed}:{u}:{s}:t"))
                    if res["auc_top"] is not None:
                        per[m][k].append(res["auc_top"])
        for m in methods:
            if all(per[m][k] for k in ks):
                vals = [statistics.fmean(per[m][k]) for k in ks]
                for k, v in zip(ks, vals):
                    curves[m][k].append(v)
                rise[m].append(vals[-1] - vals[0])
    out = {}
    for m in methods:
        d = rise[m]
        out[m] = {"auc_by_k": {k: round(statistics.fmean(curves[m][k]), 4) for k in ks if curves[m][k]},
                  "users": len(d),
                  "rose": round(sum(x > 0 for x in d) / len(d), 3) if d else None,
                  "fell": round(sum(x < 0 for x in d) / len(d), 3) if d else None,
                  "mean_rise": round(statistics.fmean(d), 4) if d else None}
    return out


def run(ratings, people, users, seed, shuffles=3):
    out = {name: {k: defaultdict(list) for k in KS} for name in METHODS}
    per_user = defaultdict(lambda: defaultdict(list))     # (method, k) -> user -> values
    for u in users:
        CURRENT["ratings"] = ratings[u]
        items = sorted(ratings[u].items())
        for s in range(shuffles):
            rng = random.Random(f"{seed}:{u}:{s}")
            order = items[:]
            rng.shuffle(order)
            for k in KS:
                if len(order) < k + 20:
                    continue
                history, test = order[:k], order[k:]
                for name, method in METHODS.items():
                    res = evaluate_one(method(history, people), test, random.Random(f"{seed}:{u}:{s}:{k}"))
                    for metric, v in res.items():
                        if v is not None:
                            out[name][k][metric].append(v)
                    if res["auc_top"] is not None:
                        per_user[(name, k)][u].append(res["auc_top"])
    return out, per_user


def by_rater(per_user, ratings, users):
    """graded vs current, split by how high the user rates on average."""
    means = sorted(users, key=lambda u: statistics.fmean(ratings[u].values()))
    third = len(means) // 3
    groups = {"strict": means[:third], "middle": means[third:2 * third], "lenient": means[2 * third:]}
    out = []
    for g, us in groups.items():
        for k in KS:
            a, b = per_user.get(("graded", k), {}), per_user.get(("B0_current", k), {})
            common = [u for u in us if u in a and u in b]
            if not common:
                continue
            d = [statistics.fmean(a[u]) - statistics.fmean(b[u]) for u in common]
            out.append({"raters": g, "k": k, "users": len(common),
                        "mean_rating": round(statistics.fmean(statistics.fmean(ratings[u].values()) for u in common), 2),
                        "graded_better": round(sum(x > 0 for x in d) / len(d), 3),
                        "graded_worse": round(sum(x < 0 for x in d) / len(d), 3),
                        "mean_diff": round(statistics.fmean(d), 4)})
    return out


def summary(out, per_user):
    rows = []
    for name in METHODS:
        for k in KS:
            a, n = out[name][k]["auc_top"], out[name][k]["ndcg10"]
            if not a:
                continue
            ci = 1.96 * statistics.pstdev(a) / math.sqrt(len(a))
            m = lambda key: round(statistics.fmean(out[name][k][key]), 4) if out[name][k][key] else None
            rows.append({"method": name, "k": k, "auc_top": round(statistics.fmean(a), 4),
                         "auc_ci95": round(ci, 4), "ndcg10": round(statistics.fmean(n), 4),
                         "coverage": m("coverage"), "auc_scored": m("auc_scored"), "cases": len(a)})
    # Per-user comparison with the current method: share of users each method beats.
    wins = []
    for name in METHODS:
        if name == "B0_current":
            continue
        for k in KS:
            a, b = per_user.get((name, k), {}), per_user.get(("B0_current", k), {})
            common = [u for u in a if u in b]
            if not common:
                continue
            d = [statistics.fmean(a[u]) - statistics.fmean(b[u]) for u in common]
            wins.append({"method": name, "k": k, "users": len(common),
                         "better": round(sum(x > 0 for x in d) / len(d), 3),
                         "worse": round(sum(x < 0 for x in d) / len(d), 3),
                         "mean_diff": round(statistics.fmean(d), 4)})
    return {"rows": rows, "vs_current": wins}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--users", type=int, default=500)
    ap.add_argument("--min-ratings", type=int, default=100)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    ratings, people = load(a.data)
    by_movie = defaultdict(list)
    for u, rs in ratings.items():
        for m, r in rs.items():
            by_movie[m].append(r)
    METHODS["reference_item_mean"] = reference_item_mean({m: (sum(v), len(v)) for m, v in by_movie.items()})
    eligible = sorted(u for u, rs in ratings.items() if len(rs) >= a.min_ratings)
    users = random.Random(a.seed).sample(eligible, min(a.users, len(eligible)))
    out, per_user = run(ratings, people, users, a.seed)
    result = summary(out, per_user)
    result["by_rater"] = by_rater(per_user, ratings, users)
    result["learning_curve_fixed_test"] = learning_curve(ratings, people, users, a.seed)
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
