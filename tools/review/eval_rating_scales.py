#!/usr/bin/env python3
"""Does person-graded-v2 still work when users rate on fewer levels, or switch
scales part-way? Checked on the same public data as eval_person_reco.py.

    python3 tools/review/eval_rating_scales.py --data DIR [--users 500] [--seed 1]

たぐりでは評価の段階を利用者が選べる（初期 5・最小 2・最大 11）。公開データは
5 段階なので、**粗い段階（2・3・4）はその人の 5 段階の評価を丸めて作る**。細かい
段階（6〜11）は作れないので確かめられない。

- 段階ごと: 学習に使う評価だけを k 段階に丸め、答え合わせは元の 5 段階のまま。
- 途中で変えた人: 学習の前半を 5 段階、後半を 2 段階（または 3 段階）で付けたと
  みなし、扱い方を 3 通り比べる。
  1. per_scale: 同じ段階の評価どうしで「いつもより高いか低いか」を出す（提案）
  2. linear: どの段階も 0〜1 に引き伸ばしてから、まとめて比べる
  3. latest_only: 変えたあとの段階の評価だけを使う
  4. per_scale_percentile: 同じ段階の評価の中での順位（0〜1 の位置）にそろえる。
     段階どうしは「その人の中での位置」で対応づける（段階の数を問わない）
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

TEST_SIZE = 40
TRAIN = 80


def coarsen(r: int, k: int) -> int:
    """A 1–5 rating on a k-level scale (k <= 5), keeping both ends."""
    return round((r - 1) * (k - 1) / 4) + 1


def graded_mixed(history, people, how="per_scale"):
    """history: [(movie, value, scale)]. Same as person-graded-v2, except how
    ratings on different scales become one 'higher/lower than usual' value."""
    if how == "per_scale_percentile":
        by = defaultdict(list)
        for _, v, k in history:
            by[k].append(v)
        acc = defaultdict(lambda: [0, 0.0])
        for m, v, k in history:
            vs = by[k]
            z = (sum(x < v for x in vs) + 0.5 * sum(x == v for x in vs)) / len(vs) - 0.5
            for rp in set(people.get(m, ())):
                acc[rp][0] += 1
                acc[rp][1] += z
        return _score(acc, people)
    if how == "latest_only":
        last = history[-1][2] if history else 5
        history = [h for h in history if h[2] == last]
    groups = defaultdict(list)
    for _, v, k in history:
        groups[k if how in ("per_scale", "latest_only") else "all"].append(
            v if how != "linear" else (v - 1) / (k - 1))
    stats = {}
    for g, vals in groups.items():
        mean = statistics.fmean(vals)
        sd = statistics.pstdev(vals) if len(vals) > 1 else 0.0
        stats[g] = (mean, sd or 1.0)
    acc = defaultdict(lambda: [0, 0.0])
    for m, v, k in history:
        g = k if how in ("per_scale", "latest_only") else "all"
        x = v if how != "linear" else (v - 1) / (k - 1)
        mean, sd = stats[g]
        z = (x - mean) / sd
        for rp in set(people.get(m, ())):
            acc[rp][0] += 1
            acc[rp][1] += z
    return _score(acc, people)


def _score(acc, people):
    def score(m):
        parts = [s / (n + E.CONF_K) * E.ROLE_W[role] for (role, p) in set(people.get(m, ()))
                 if (n_s := acc.get((role, p))) for n, s in [n_s]]
        if not parts:
            return None
        pos = sorted((x for x in parts if x > 0), reverse=True)[:E.TOP_N]
        neg = sorted(x for x in parts if x < 0)[:E.TOP_N]
        return sum(pos) + sum(neg)
    return score


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--users", type=int, default=500)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--shuffles", type=int, default=3)
    a = ap.parse_args()
    ratings, people = E.load(a.data)
    eligible = sorted(u for u, rs in ratings.items() if len(rs) >= TRAIN + TEST_SIZE)
    users = random.Random(a.seed).sample(eligible, min(a.users, len(eligible)))
    res = defaultdict(lambda: defaultdict(list))        # condition -> user -> aucs
    for u in users:
        items = sorted(ratings[u].items())
        for s in range(a.shuffles):
            rng = random.Random(f"sc:{a.seed}:{u}:{s}")
            order = items[:]
            rng.shuffle(order)
            test, train = order[-TEST_SIZE:], order[:TRAIN]
            trng = lambda: random.Random(f"sc:{a.seed}:{u}:{s}:t")
            def run(name, history, how="per_scale"):
                r = E.evaluate_one(graded_mixed(history, people, how), test, trng())
                if r["auc_top"] is not None:
                    res[name][u].append(r["auc_top"])
            for k in (5, 4, 3, 2):
                run(f"fixed_{k}", [(m, coarsen(r, k), k) for m, r in train])
            half = TRAIN // 2
            for k2 in (2, 3):
                mixed = [(m, r, 5) for m, r in train[:half]] + [(m, coarsen(r, k2), k2) for m, r in train[half:]]
                for how in ("per_scale", "per_scale_percentile", "linear", "latest_only"):
                    run(f"switch_5to{k2}_{how}", mixed, how)
    out = {}
    base = res["fixed_5"]
    for name, per in res.items():
        common = [u for u in per if u in base]
        means = [statistics.fmean(per[u]) for u in common]
        d = [statistics.fmean(per[u]) - statistics.fmean(base[u]) for u in common]
        out[name] = {"users": len(common), "auc": round(statistics.fmean(means), 4),
                     "ci95": round(1.96 * statistics.pstdev(means) / len(means) ** 0.5, 4),
                     "vs_5_levels": round(statistics.fmean(d), 4),
                     "worse_than_5": round(sum(x < 0 for x in d) / len(d), 3)}
    # Paired: the proposed per-scale handling against the alternatives.
    for k2 in (2, 3):
        for other in ("linear", "latest_only", "per_scale_percentile"):
            x, y = res[f"switch_5to{k2}_per_scale"], res[f"switch_5to{k2}_{other}"]
            common = [u for u in x if u in y]
            d = [statistics.fmean(x[u]) - statistics.fmean(y[u]) for u in common]
            out[f"per_scale_minus_{other}_5to{k2}"] = {
                "mean_diff": round(statistics.fmean(d), 4),
                "ci95": round(1.96 * statistics.pstdev(d) / len(d) ** 0.5, 4),
                "per_scale_better": round(sum(v > 0 for v in d) / len(d), 3),
                "per_scale_worse": round(sum(v < 0 for v in d) / len(d), 3)}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
