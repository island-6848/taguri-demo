#!/usr/bin/env python3
"""Compare the current ordinal z with "anchored" versions that keep the good
grades positive, on public data (q-anchored-ordinal).

    python3 tools/review/eval_anchored_ordinal.py --data DIR [--users 500] [--seed 1]

起案者の指摘（2026-10-20）「◎が多かったからって◯のzがマイナスになるのはまずい。せめて◎◯は常に+」。
今の z（式 1–2）は本人の評価の中での位置なので平均が 0 になり、甘めの人の ○・★4 が負になる。
真ん中の段（Douban の 1〜5 では ★3）に錨を置く 2 案を、今の z と同じ手順で比べる:
- current  z = √12·(F − ½)                     （person-ordinal-v3、本番）
- side     真ん中は 0。上の段は上側の評価の中での位置で 0〜√3、下の段は下側の中で −√3〜0（案 1）
- shift    z = √12·(F − F(真ん中))              （案 2）
- clip     今の z のまま、真ん中より上の段は 0 未満にしない・下の段は 0 より上にしない（案 3）
- clip_same  clip に加えて、評価がみな同じ段の人は、その評価を仮の好み（お気に入りと同じ z0 ＝ SEED_Z、
             重み SEED_K/(SEED_K+件数)）として数える。真ん中より下の段なら負、真ん中なら 0（q-all-same-ratings-no-reco の案 1）
F は中央順位（下の数 ＋ 同じ数の半分）／件数。

Protocol, users, measures and the scorer are eval_design_choices' (per user,
3 random orders, the last 40 ratings fixed for checking, the first k = 10/40/80
seen; auc_top and pairs, averaged). Other settings are the production ones
(k = 3, director 0.4, top 3 + 3, genre types weight 1.0); only the grade differs.
Results are also split by how high the user rates (mean ≥ 4 = lenient).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import random
import statistics
from pathlib import Path

spec = importlib.util.spec_from_file_location("DC", Path(__file__).with_name("eval_design_choices.py"))
DC = importlib.util.module_from_spec(spec)
spec.loader.exec_module(DC)

SEED_Z, SEED_K = 0.4 * math.sqrt(12), 3     # user_recommender.SEED_Z / SEED_K
NEUTRAL = 3          # Douban 1–5: ★3 is the middle (起案者: 「微妙なのって△とか3〜3.7あたり」)
PARAMS = dict(DC.CURRENT, grade="percentile", genre=1.0)


def grade_values(history, how):
    rs = [r for _, r in history]
    n = len(rs)
    def F(r):
        return (sum(v < r for v in rs) + 0.5 * sum(v == r for v in rs)) / n
    below = sum(v < NEUTRAL for v in rs) / n
    above = sum(v > NEUTRAL for v in rs) / n
    mid = below + 0.5 * sum(v == NEUTRAL for v in rs) / n
    def z(r):
        if how == "current":
            return math.sqrt(12) * (F(r) - 0.5)
        if how == "shift":
            return math.sqrt(12) * (F(r) - mid)
        if how == "clip_same" and len(set(rs)) == 1:
            sign = (r > NEUTRAL) - (r < NEUTRAL)
            return sign * SEED_Z * SEED_K / (SEED_K + n)
        if how in ("clip", "clip_same"):
            x = math.sqrt(12) * (F(r) - 0.5)
            return max(x, 0.0) if r > NEUTRAL else min(x, 0.0) if r < NEUTRAL else x
        if r == NEUTRAL:
            return 0.0
        if r > NEUTRAL:
            return math.sqrt(3) * (F(r) - (1 - above)) / above
        return -math.sqrt(3) * (below - F(r)) / below
    return [(m, z(r)) for m, r in history]


def all_same(users, ratings, people, types, seed, shuffles=3):
    """Only the cases where the first k ratings are all one grade (the case
    q-all-same-ratings-no-reco is about): how often, and the measure there."""
    out = {}
    for how in ("current", "clip", "clip_same"):
        DC.values = lambda history, p, how=how: grade_values(history, how)
        got = {k: [] for k in (5, 10)}
        for u in users:
            items = sorted(ratings[u].items())
            for sh in range(shuffles):
                order = items[:]
                random.Random(f"dc:{seed}:{u}:{sh}").shuffle(order)
                test, train = order[-DC.TEST_SIZE:], order[:-DC.TEST_SIZE]
                for k in got:
                    if len({r for _, r in train[:k]}) != 1:
                        continue
                    f = DC.scorer(train[:k], people, types, PARAMS)
                    r = DC.E.evaluate_one(f, test, random.Random(f"dc:{seed}:{u}:{sh}:t"))
                    pa = DC.pair_accuracy(f, test)
                    if r["auc_top"] is not None and pa is not None:
                        got[k].append((r["auc_top"] + pa) / 2)
        out[how] = {f"k{k}": {"cases": len(v), "mean": round(statistics.fmean(v), 4) if v else None} for k, v in got.items()}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--users", type=int, default=500)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    ratings, people = DC.E.load(a.data)
    types = DC.load_types(a.data / "movie_type.dat")
    eligible = sorted(u for u, rs in ratings.items() if len(rs) >= max(DC.KS) + DC.TEST_SIZE)
    random.Random(a.seed).shuffle(eligible)
    users = eligible[:a.users]
    lenient = {u for u in users if statistics.fmean(ratings[u].values()) >= 4}
    out = {"users": len(users), "lenient_users": len(lenient), "methods": {}}
    per_user = {}
    for how in ("current", "side", "shift", "clip", "clip_same"):
        DC.values = lambda history, p, how=how: grade_values(history, how)
        m, pu = DC.evaluate(PARAMS, users, ratings, people, types, a.seed)
        per_user[how] = pu
        out["methods"][how] = {f"k{k}": round(v, 4) for k, v in m.items()} | {"detail": DC.evaluate.parts}
    for how in ("side", "shift", "clip", "clip_same"):
        cmp = {}
        for k in DC.KS:
            for name, group in (("all", users), ("lenient", lenient)):
                common = [u for u in group if u in per_user[how][k] and u in per_user["current"][k]]
                d = [per_user[how][k][u] - per_user["current"][k][u] for u in common]
                cmp[f"k{k}_{name}"] = {"diff": round(statistics.fmean(d), 4),
                                       "ci95": round(1.96 * statistics.pstdev(d) / len(d) ** 0.5, 4),
                                       "better_users": round(sum(x > 0 for x in d) / len(d), 3), "n": len(d)}
        out[f"{how}_vs_current"] = cmp
    out["all_same"] = all_same(users, ratings, people, types, a.seed)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
