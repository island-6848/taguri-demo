#!/usr/bin/env python3
"""劇場の**規模の段階**で評価に差が出るかを測る（V76）。

## なぜ会場そのものではなく段階を測るのか

**会場ごとの当たり率はすでに測って落としてある**（[検証 019](../../docs/verification/019-scoring-fixes.md)）
── 基準より 0.15 以上低い会場は 0 件、高い 3 件はいずれも n=2 の偶然だった。
[検証 002](../../docs/verification/002-first-seven-records.md) では、会場への不満が
公演の評価が ○ のときにも書かれていた（**会場の評価と公演の評価は独立している**）。

**それでも「規模の段階」は測っていない。**
[検証 001](../../docs/verification/001-theater-capacity.md) で「客席数は単一の値に
ならないので段階（小・中・大）で持つ」と設計したままである。**粒度を上げてまとめ直す
ことは、会場を 1 つずつ数えるのとは別の操作**なので、落とした判定の中に含まれていない。

## 交絡を必ず除く

[検証 016](../../docs/verification/016-troupe-is-a-confounder.md) の失敗をくり返さない。
団体「東宝」の当たり率 0.89 は**劇団1・作り手12が出ていたからで、団体の力では
なかった。** 規模でも同じことが起きうる（大劇場に好きな出演者が多いなら、規模が
効いているように見える）。**名簿（網 B）の強さで層に分け、層の中でも差が残るかを見る。**

    python3 tools/review/measure_venue_size.py

材料は `data/stages/theaters.json`（`tools/stages/fetch_theater_info.py` が作る）と
`data/review/ratings.db`。どちらも端末内のファイルで、外へは何も出さない。
"""

from __future__ import annotations

import collections
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "review"))
sys.path.insert(0, str(ROOT / "tools" / "taguri"))
import measure_nets as M                                            # noqa: E402
import venues as V                                                  # noqa: E402

INFO = ROOT / "data" / "stages" / "theaters.json"
BANDS = ("小", "中", "大")
MIN_BAND = 5      # これ未満の段は読み方に入れない（n=2 の段が結論に出てしまう）
MIN_CELL = 5      # 層に分けたあとの 1 マスの下限


def _info() -> dict:
    return json.loads(INFO.read_text(encoding="utf-8")) if INFO.exists() else {}


def bands_of_works() -> dict[str, str]:
    """作品の鍵 → 規模の段階。**段階が 1 つに決まらない作品は「不明」にする。**

    巡演で規模の違うホールを回った作品があり、片方を代表に選ぶと段階が恣意になる。
    """
    import app as APP                                               # noqa: E402
    info = _info()
    out = {}
    for w in APP._works():
        bs = set()
        for s in w.get("shows") or []:
            if not s.get("venue"):
                continue
            g = info.get(V.hall(s["venue"])) or {}
            if g.get("seats"):
                bs.add(g["band"])
        out[w["work_key"]] = bs.pop() if len(bs) == 1 else "不明"
    return out


def main() -> int:
    rated = M.load_rated()
    if not rated:
        print("評価が付いた作品がありません。")
        return 1
    band = bands_of_works()
    # **網 B の強さは 1 件を伏せて出す**（自分の評価で自分を当てないため）
    _auc, pairs = M.leave_one_out(
        rated, lambda v: M.WEIGHT.get(v, 0.0), by_role=True,
        target=lambda v: v == "◎")
    strength = {r["key"]: s for r, (s, _y) in zip(rated, pairs)}

    rows = [(r, band.get(r["key"], "不明"), strength.get(r["key"], 0.0)) for r in rated]
    have = [x for x in rows if x[1] in BANDS]
    print(f"■ 分母 ── 評価が付いた作品 {len(rated)} 件のうち、"
          f"規模が決まったのは {len(have)} 件")
    miss = collections.Counter()
    for r, b, _ in rows:
        if b == "不明":
            miss["会場が取れていない／段階が決まらない"] += 1
    if miss:
        # **あふれた分の行き先を言う。** 分母から外した件数を黙って落とさない
        print(f"   （残り {sum(miss.values())} 件は会場が取れていないか、"
              f"巡演で段階が 1 つに決まらない）")
    if not have:
        return 1

    def rate(xs) -> tuple[int, float, float]:
        n = len(xs)
        pos = sum(1 for r, _, _ in xs if r["verdict"] == "◎")
        wt = statistics.fmean(M.WEIGHT.get(r["verdict"], 0.0) for r, _, _ in xs)
        return n, pos / n, wt

    base_n, base_r, base_w = rate(have)
    print(f"\n■ 全体 ── {base_n} 件・◎ が {base_r:.0%}・重み平均 {base_w:.2f}")
    print("\n■ 規模の段階ごと")
    print(f"   {'段階':<6}{'件数':>5}{'◎ の率':>9}{'重み平均':>9}{'名簿の強さ':>11}")
    for b in BANDS:
        xs = [x for x in have if x[1] == b]
        if not xs:
            continue
        n, r, w = rate(xs)
        st = statistics.fmean(x[2] for x in xs)
        print(f"   {b:<6}{n:>5}{r:>9.0%}{w:>9.2f}{st:>11.3f}")

    # **交絡を除く。** 名簿に一致があるかどうかで分け、層の中でも差が残るかを見る。
    # **中央値で切らない** ── 一致が無い作品の強さはちょうど 0 で、全体の半分を占める。
    # 中央値は 0 になるので「弱い側」の意味が「一致が無い」と同じになり、
    # 数字だけが分かりにくくなる
    print("\n■ 名簿（網 B）に一致があるかで分けた ◎ の率")
    print(f"   {'段階':<6}{'一致なし':>14}{'一致あり':>14}")
    inter = {}
    for b in BANDS:
        lo = [x for x in have if x[1] == b and x[2] <= 0]
        hi = [x for x in have if x[1] == b and x[2] > 0]
        f = lambda xs: (f"{sum(1 for r, _, _ in xs if r['verdict'] == '◎') / len(xs):.0%}"
                        f"（{len(xs)}）" if xs else "──")
        print(f"   {b:<6}{f(lo):>14}{f(hi):>14}")
        if len(lo) >= MIN_CELL and len(hi) >= MIN_CELL:
            inter[b] = (sum(1 for r, _, _ in lo if r["verdict"] == "◎") / len(lo),
                        sum(1 for r, _, _ in hi if r["verdict"] == "◎") / len(hi))

    print("\n■ 読み方")
    xs = {b: rate([x for x in have if x[1] == b]) for b in BANDS
          if len([x for x in have if x[1] == b]) >= MIN_BAND}
    thin = [b for b in BANDS if 0 < len([x for x in have if x[1] == b]) < MIN_BAND]
    if thin:
        # **件数の少ない段を読み方に混ぜない。** n=2 の段が「いちばん高い」として
        # 結論に出てしまう（実際に 1 度そうなった）
        print(f"   段階「{'・'.join(thin)}」は {MIN_BAND} 件未満なので読み方に入れない。")
    if len(xs) < 2:
        print(f"   比べられる段階が {len(xs)} つしかない。")
    else:
        hi = max(xs, key=lambda b: xs[b][1])
        lo = min(xs, key=lambda b: xs[b][1])
        d = xs[hi][1] - xs[lo][1]
        if d < 0.05:
            print(f"   **規模そのものでは差が出ない。**"
                  + "・".join(f"「{b}」{xs[b][1]:.0%}（{xs[b][0]} 件）" for b in xs)
                  + f" で、いちばん高い段と低い段の差は {d:.0%} しかない。")
        else:
            st = {b: statistics.fmean(x[2] for x in have if x[1] == b) for b in xs}
            print(f"   ◎ の率がいちばん高いのは「{hi}」（{xs[hi][1]:.0%}・{xs[hi][0]} 件）、"
                  f"低いのは「{lo}」（{xs[lo][1]:.0%}・{xs[lo][0]} 件）で、差は {d:.0%}。"
                  + (f"ただし「{hi}」は名簿の強さの平均も高い"
                     f"（{st[hi]:.3f} 対 {st[lo]:.3f}）── **規模ではなく、そこに出ていた人で"
                     f"説明できる可能性がある。**" if st[hi] > st[lo] else
                     f"名簿の強さの平均は「{hi}」のほうが低い（{st[hi]:.3f} 対 {st[lo]:.3f}）"
                     f"── 出ていた人では説明できない差である。"))
    # **主効果ではなく、交互作用を見る。** 規模で当たり率は変わらなくても、
    # 規模によって「名簿がどれだけ効くか」が変わるなら、それは使える知識である
    if len(inter) >= 2:
        gap = {b: hi - lo for b, (lo, hi) in inter.items()}
        strong = max(gap, key=lambda b: gap[b])
        weak = min(gap, key=lambda b: gap[b])
        if gap[strong] - gap[weak] >= 0.2:
            print(f"\n   **効くのは規模ではなく、規模によって名簿の効き方が変わることである。**"
                  f"「{strong}」では一致なし {inter[strong][0]:.0%} → 一致あり"
                  f" {inter[strong][1]:.0%}（差 {gap[strong]:.0%}）だが、"
                  f"「{weak}」では {inter[weak][0]:.0%} → {inter[weak][1]:.0%}"
                  f"（差 {gap[weak]:.0%}）しか動かない。")
            print(f"   つまり **「{strong}」の候補は名簿の一致を信じてよく、"
                  f"「{weak}」の候補は名簿だけでは決められない。**")
    print("\n■ 限界（結論の数字の側にも効く）")
    print(f"   ・**標本は 1 名・{len(have)} 件である。** ここで差が出ても出なくても、"
          "仕組みから規模の軸を落とす／入れる根拠には足りない")
    print(f"   ・会場は購入確認メールから取っている。**メールに劇場名が載らない発行元が"
          f"あり、評価が付いた {len(rated)} 件のうち {len(rated) - len(have)} 件は"
          "この測定に入っていない**（載る発行元に偏っている）")
    print("   ・座席数は可変の劇場では代表値である（検証 001）。段階に丸めているので"
          "多くは吸収されるが、境界の劇場では段階が動きうる")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
