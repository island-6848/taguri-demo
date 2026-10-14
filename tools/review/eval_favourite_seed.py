#!/usr/bin/env python3
"""Does seeding the recommender from a user's declared favourites help, and
for how long? Public data (Douban movies), per user, own data only.

    python3 tools/review/eval_favourite_seed.py --data DIR --types FILE [--seed 1]

たぐり asks for favourites ("people you always want to follow") before any
rating. The idea under test (q-favourites-seed): treat the favourite's other
productions as pseudo ratings in the user's top fifth, weighted
K / (K + real ratings) so real ratings take over, and leave out the favourite
themself (their own shows are listed separately), so the seed reaches the
people they work with and the kinds of show they do.

Simulation, per user and random order (3 orders):
- the last 40 ratings are the check set; the 40 before them stand in for what
  the user knows before signing up: people appearing at least twice there
  with every rating at the user's top grade become the favourites (at most 3;
  users with none are skipped, as nothing would change for them);
- the method sees the first k of the remaining ratings (k = 0, 3, 10, 20, 40, 80);
- seeds: the favourites' other movies, not in the check set (at most 60).
Scorer: person-ordinal-v3 as in eval_design_choices (percentile, k = 3,
director 0.4, top 3 up / 3 down, genre 1.0). Measures as there (auc_top,
pairs). Settings are chosen on one group of users and confirmed on another.

Caveat: favourites here are picked from the user's own high ratings, so they
are surely liked; declared favourites may be weaker or stronger signals.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


E = _load("eval_person_reco")
D = _load("eval_design_choices")

KS = (0, 3, 10, 20, 40, 80)
TEST, ASIDE, MAX_SEEDS, MAX_FAVS = 40, 40, 60, 3
SQRT12 = math.sqrt(12)
PARAMS = {"grade": "percentile", "agg": "mean", "k": 3, "dir_w": 0.4, "top": 3, "genre": 1.0}
GRID = [{"z": 0.0, "K": 5, "own": False}]  # no seed
GRID += [{"z": z, "K": K, "own": own} for z in (0.4 * SQRT12, 0.2 * SQRT12)
         for K in (3, 10, 30, None) for own in (False, True)]


def favourites(aside, people, kind="person", types=None):
    """Favourites a user would declare, from the aside ratings.

    kind "person": people (actors, directors) rated at the top every time, at
    least twice. "director": directors only — stands in for a troupe or
    producer (a set of productions sharing a recurring creative core).
    "genre": a genre rated near the top (mean within half a grade of the top,
    at least 3 movies) — stands in for a subject (題材). Genres are returned
    as ("genre", name)."""
    top = max(r for _, r in aside)
    seen = defaultdict(list)
    if kind == "genre":
        for m, r in aside:
            for t in set(types.get(m, ())):
                seen[("genre", t)].append(r)
        favs = sorted((g for g, rs in seen.items() if len(rs) >= 3 and statistics.fmean(rs) >= top - 0.5),
                      key=lambda g: (-statistics.fmean(seen[g]), -len(seen[g]), g))
        return favs[:1]
    for m, r in aside:
        for rp in set(people.get(m, ())):
            if kind == "director" and rp[0] != "director":
                continue
            seen[rp].append(r)
    favs = sorted((rp for rp, rs in seen.items() if len(rs) >= 2 and all(r == top for r in rs)),
                  key=lambda rp: (-len(seen[rp]), rp))
    return favs[:MAX_FAVS]


def scorer(history, seeds, favs, people, types, s):
    """person-ordinal-v3 with seed pseudo ratings (value s['z'], weight w)."""
    w = 1.0 if s["K"] is None else s["K"] / (s["K"] + len(history))
    roles = {"actor": 1.0, "director": PARAMS["dir_w"]}
    acc, gacc = defaultdict(lambda: [0.0, 0.0]), defaultdict(lambda: [0.0, 0.0])
    for m, x in D.values(history, PARAMS) if history else []:
        x *= SQRT12
        for rp in set(people.get(m, ())):
            acc[rp][0] += 1
            acc[rp][1] += x
        for t in set(types.get(m, ())):
            gacc[t][0] += 1
            gacc[t][1] += x
    if s["z"]:
        fav = set(favs)
        for m in seeds:
            for rp in set(people.get(m, ())):
                if rp in fav and not s["own"]:
                    continue
                acc[rp][0] += w
                acc[rp][1] += w * s["z"]
            for t in set(types.get(m, ())):
                if ("genre", t) in fav and not s["own"]:
                    continue
                gacc[t][0] += w
                gacc[t][1] += w * s["z"]

    def score(m):
        parts = [acc[(role, q)][1] / (acc[(role, q)][0] + PARAMS["k"]) * roles[role]
                 for role, q in set(people.get(m, ())) if (role, q) in acc]
        pos = sorted((v for v in parts if v > 0), reverse=True)[:3]
        neg = sorted(v for v in parts if v < 0)[:3]
        g = [gacc[t][1] / (gacc[t][0] + 3) for t in set(types.get(m, ())) if t in gacc]
        out = sum(pos) + sum(neg) + (PARAMS["genre"] * statistics.fmean(g) if g else 0.0)
        return out if (parts or g) else None
    return score


def evaluate(settings, users, ratings, people, types, by_person, seed, shuffles=3, kind="person"):
    """{k: mean over users of (auc_top + pairs)/2} per setting index, and per user."""
    per_user = [{k: {} for k in KS} for _ in settings]
    for u in users:
        items = sorted(ratings[u].items())
        got = [{k: [] for k in KS} for _ in settings]
        for sh in range(shuffles):
            rng = random.Random(f"fs:{seed}:{u}:{sh}")
            order = items[:]
            rng.shuffle(order)
            test, aside, train = order[-TEST:], order[-TEST - ASIDE:-TEST], order[:-TEST - ASIDE]
            favs = favourites(aside, people, kind, types)
            if not favs:
                continue
            test_ids = {m for m, _ in test}
            pool = sorted({m for f in favs for m in by_person[f]} - test_ids)
            seeds = random.Random(f"fs:{seed}:{u}:{sh}:s").sample(pool, min(MAX_SEEDS, len(pool)))
            for i, s in enumerate(settings):
                for k in KS:
                    f = scorer(train[:k], seeds, favs, people, types, s)
                    r = E.evaluate_one(f, test, random.Random(f"fs:{seed}:{u}:{sh}:t"))
                    pa = D.pair_accuracy(f, test)
                    if r["auc_top"] is not None and pa is not None:
                        got[i][k].append((r["auc_top"] + pa) / 2)
        for i in range(len(settings)):
            for k in KS:
                if got[i][k]:
                    per_user[i][k][u] = statistics.fmean(got[i][k])
    means = [{k: statistics.fmean(pu[k].values()) if pu[k] else None for k in KS} for pu in per_user]
    return means, per_user


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--types", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--tune-users", type=int, default=300)
    ap.add_argument("--test-users", type=int, default=500)
    ap.add_argument("--kind", choices=("person", "director", "genre"), default="person")
    a = ap.parse_args()
    ratings, people = E.load(a.data)
    types = D.load_types(a.types)
    by_person = defaultdict(list)
    for m, ps in people.items():
        for rp in set(ps):
            by_person[rp].append(m)
    for m, ts in types.items():
        for t in set(ts):
            by_person[("genre", t)].append(m)
    eligible = sorted(u for u, rs in ratings.items() if len(rs) >= max(KS) + TEST + ASIDE)
    rng = random.Random(a.seed)
    rng.shuffle(eligible)
    tune, check = eligible[:a.tune_users], eligible[a.tune_users:a.tune_users + a.test_users]
    means, _ = evaluate(GRID, tune, ratings, people, types, by_person, a.seed, kind=a.kind)
    rows = [{"setting": s, **{f"k{k}": round(m[k], 4) for k in KS}} for s, m in zip(GRID, means)]
    # Chosen on the mean over k (every stage of use counts), never below no-seed at any k.
    base = means[0]
    ok = [i for i in range(1, len(GRID)) if all(means[i][k] >= base[k] - 0.002 for k in KS)]
    best = max(ok or [0], key=lambda i: statistics.fmean(means[i].values()))
    out = {"kind": a.kind, "tune_users": len(tune), "check_users": len(check), "grid": rows, "chosen": GRID[best]}
    m2, pu = evaluate([GRID[0], GRID[best]], check, ratings, people, types, by_person, a.seed + 100, kind=a.kind)
    conf = {}
    for k in KS:
        common = [u for u in pu[1][k] if u in pu[0][k]]
        d = [pu[1][k][u] - pu[0][k][u] for u in common]
        conf[k] = {"no_seed": round(m2[0][k], 4), "seed": round(m2[1][k], 4),
                   "diff": round(statistics.fmean(d), 4),
                   "ci95": round(1.96 * statistics.pstdev(d) / len(d) ** 0.5, 4),
                   "better_users": round(sum(x > 0 for x in d) / len(d), 3),
                   "worse_users": round(sum(x < 0 for x in d) / len(d), 3), "users": len(d)}
    out["confirm_on_heldout"] = conf
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
