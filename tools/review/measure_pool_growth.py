#!/usr/bin/env python3
"""履歴が増えると、期待度が付く候補は何件まで増えるのかを実測する。

## なぜ測るのか

[検証 037](../../docs/verification/037-first-day-guarantee.md) の「期待度が付いた 118 件」は
**評価済み 91 作品での値**である。起案者の指摘 ── **「長期的な運用をしていくと、
最初から期待度のつく公演数が増加してしまうと思うが、その制御はどう考えているか」。**

名簿は履歴から作るので、**履歴が増えれば名簿の人物が増え、候補に一致する確率も上がる。**
週 15 件で足りるという結論は、期待度が付く件数が増えれば崩れる。**増え方を測る。**

## 測り方

評価済み作品を**古い順**に N 作品だけ使って名簿と内容の傾向を作り、候補 869 件のうち
**強さが正になる件数**を数える。N を 20, 30, … と増やして曲線を見る。

    python3 tools/review/measure_pool_growth.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "review"))
import measure_nets as M      # noqa: E402
import net_c as C             # noqa: E402

CAND = ROOT / "data" / "review" / "candidates.jsonl"


def main() -> int:
    rated_all = sorted(M.load_rated(), key=lambda r: r["date"] or "")
    cands = [json.loads(l) for l in CAND.read_text(encoding="utf-8").split("\n") if l.strip()]
    themes = C.load_themes()
    pos = lambda v: 1.0 if v == "◎" else 0.0        # noqa: E731
    print(f"評価済み {len(rated_all)} 作品（古い順）／候補 {len(cands)} 件\n")
    print(" 履歴 | 名簿の行 | 網 B が付く | 網 C が付く | どちらか | 両方 | 割合")
    rows = []
    for n in [20, 30, 40, 50, 60, 70, 80, len(rated_all)]:
        if n > len(rated_all):
            continue
        rated = rated_all[:n]
        base = sum(pos(r["verdict"]) for r in rated) / max(len(rated), 1)
        roster = M.build_roster(rated, pos)
        lift = C.build_lift(rated, themes, pos)
        nb = nc = both = 0
        for c in cands:
            b = M.score({"people": M.parse_credits(c.get("fields") or {})}, roster, base)
            th = themes.get(("candidate", c["stage_id"]))
            s, _ = C.strength(C.words(th), lift)
            if b > 0:
                nb += 1
            if s > 0:
                nc += 1
            if b > 0 and s > 0:
                both += 1
        either = nb + nc - both
        rows.append((n, len(roster), nb, nc, either, both))
        print(f" {n:>4} | {len(roster):>8} | {nb:>10} | {nc:>10} | {either:>7} | {both:>4} |"
              f" {either / len(cands):>5.1%}")

    # 直線で伸ばすと、履歴が何作品でどれだけになるか
    if len(rows) >= 2:
        (n1, _, _, _, e1, _), (n2, _, _, _, e2, _) = rows[-2], rows[-1]
        slope = (e2 - e1) / max(n2 - n1, 1)
        print(f"\n 直近の傾き: 履歴 1 作品あたり {slope:+.2f} 件")
        for target in (150, 200, 300):
            print(f"   履歴 {target} 作品なら 約 {e2 + slope * (target - n2):.0f} 件"
                  f"（候補 {len(cands)} 件の {min((e2 + slope * (target - n2)) / len(cands), 1):.0%}）"
                  " ※直線で伸ばした粗い外挿")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
