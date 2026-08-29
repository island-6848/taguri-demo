#!/usr/bin/env python3
"""採点の式のうち、どの部分が実測で裏づいているかを 1 つずつ差し替えて測る。

`recommend2.py` の採点は定数が 5 つある ── 正例の切り方・平滑化・信頼度の定数・
役職の重み・足す人数。**測って決めたものと、設計のまま置いてあるものが混ざっている。**
1 つずつ変えて leave-one-out の AUC を出し、**変えても動かない定数**を洗い出す。

差が偶然かどうかは、作品を復元抽出して 200 回取り直した対の差で見る（同じ標本で比べる）。

    python3 tools/review/audit_scoring.py
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "review"))
import measure_nets as M                                  # noqa: E402

# 実装の重み（検証 019 で単独 AUC から置いた）
ROLE_W_NOW = {"出演": 1.0, "演出": 0.4, "脚本": 0.4, "作": 0.4, "原作": 0.4, "翻訳": 0.3}
BACKSTAGE_NOW = 0.1
# 企画書 4 章の当初案
ROLE_W_OLD = {"出演": 0.6, "演出": 1.0, "脚本": 1.0, "作": 1.0, "原作": 1.0}
BACKSTAGE_OLD = 0.4

IS_TOP = staticmethod(lambda v: v == "◎")


def score(row, roster, base, *, role_w, backstage, top_n, conf_k, smooth):
    parts = []
    for role, person in row["people"]:
        n, o = roster.get((role, person), (0, 0))
        if n == 0:
            continue
        a, b = smooth
        rate = (o + a) / (n + b)
        conf = n / (n + conf_k) if conf_k else 1.0
        w = role_w.get(role, backstage)
        c = (rate - base) * conf * w
        if c > 0:
            parts.append(c)
    parts.sort(reverse=True)
    return sum(parts[:top_n] if top_n else parts)


def loo(rows, **kw):
    """1 件を伏せて残りから名簿を作り、その 1 件を当てる。"""
    out = []
    for i, r in enumerate(rows):
        rest = rows[:i] + rows[i + 1:]
        roster = M.build_roster(rest, lambda v: v == "◎")
        base = sum(v["verdict"] == "◎" for v in rest) / len(rest)
        out.append((score(r, roster, base, **kw), r["verdict"] == "◎"))
    return out


BASE_CFG = dict(role_w=ROLE_W_NOW, backstage=BACKSTAGE_NOW, top_n=3, conf_k=3, smooth=(1, 2))

VARIANTS = [
    ("現行の式", {}),
    ("裏方を外す（重み 0）", dict(backstage=0.0)),
    ("役職の重みを一律 1.0", dict(role_w={}, backstage=1.0)),
    ("企画書 4 章の当初の重み", dict(role_w=ROLE_W_OLD, backstage=BACKSTAGE_OLD)),
    ("足すのは 1 名だけ", dict(top_n=1)),
    ("足すのは 5 名", dict(top_n=5)),
    ("全員の和", dict(top_n=None)),
    ("信頼度の定数 3 → 1", dict(conf_k=1)),
    ("信頼度の定数 3 → 10", dict(conf_k=10)),
    ("信頼度を使わない", dict(conf_k=0)),
    ("平滑化しない (o/n)", dict(smooth=(0, 0))),
    ("平滑化を強める (+2/+4)", dict(smooth=(2, 4))),
]


def main() -> int:
    rows = M.load_rated()
    print(f"評価済み {len(rows)} 作品（◎ {sum(1 for r in rows if r['verdict'] == '◎')} 件）\n")
    pairs = {}
    for name, over in VARIANTS:
        cfg = dict(BASE_CFG, **over)
        try:
            pairs[name] = loo(rows, **cfg)
        except ZeroDivisionError:
            continue
    ref = pairs["現行の式"]
    rnd = random.Random(20260821)
    idx = list(range(len(rows)))
    print(f"{'変えたところ':28s} {'AUC':>6s}  {'現行との差':>9s}  {'差が正だった割合（200 回）':>12s}")
    for name, pr in pairs.items():
        a = M.auc(pr)
        if name == "現行の式":
            print(f"{name:28s} {a:6.3f}  {'──':>9s}")
            continue
        # 同じ標本で対にして比べる（復元抽出 200 回）
        wins = 0
        for _ in range(200):
            s = [rnd.choice(idx) for _ in idx]
            x, y = M.auc([pr[i] for i in s]), M.auc([ref[i] for i in s])
            if x is None or y is None:
                continue
            wins += x > y
        print(f"{name:28s} {a:6.3f}  {a - M.auc(ref):+9.3f}  {wins / 200:>12.0%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
