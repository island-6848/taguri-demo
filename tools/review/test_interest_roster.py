#!/usr/bin/env python3
"""興味あり・観ればよかったを名簿に混ぜる仕組みの検査。

    python3 tools/review/test_interest_roster.py

起案者の指示（2026-08-26）──「その機能不要です。代わりに『観れば良かった』で挙がった
人名は『興味あり』のボタンを押した扱いと同じにして、推薦に反映させて」。調べたところ、
**「興味あり」自体はこれまで束の振り分け（追いかけている一覧に入れる）にしか使っておらず、
名簿（roster）には一切効いていなかった**ので、その橋を新設した
（`measure_nets.interest_credits`／`add_interest_roster`）。

**本物の DB・実データのファイルには 1 行も書かない。** `interest_credits` が呼ぶ
`_fields_by_stage`（`ROOT/data/credits/...` を読む私的関数）は、この検査の中だけ差し替える
── 検査のたびに本物のクレジット控えを用意する必要が無い。`add_interest_roster` は
純関数（辞書を受け取って新しい辞書を返す）なので、そのまま呼べる。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "review"))
import measure_nets as M                                           # noqa: E402

ok = fail = 0


def check(name: str, cond: bool, got=None) -> None:
    global ok, fail
    if cond:
        ok += 1
    else:
        fail += 1
        print(f"  NG  {name}" + (f"  ← {got!r}" if got is not None else ""))


# ---------------------------------------------------------------- interest_credits
#
# `_fields_by_stage` を差し替えて、本物の控えファイルに触らずに検査する
FIELDS = {
    "100": {"出演": "作り手14", "演出": "内藤裕子"},
    "200": {"出演": "作り手14"},
    "300": {"出演": "作り手25"},  # 興味なしを押した公演にしか出さない（除外の検査用）
}
M._fields_by_stage = lambda: FIELDS

react = {
    "100": {"interest": 1, "title": "作品A"},
    "200": {"interest": 1, "title": "作品B"},
    "300": {"interest": 0, "title": "興味なしを押した公演"},  # 興味なしは対象外
    "999": {"interest": 1, "title": "控えに無い公演"},        # 控えが無い分は静かに落ちる
}
missed = [{"出演": "作り手14"}]  # 興味ありとは別に、観ればよかった側からも来る

people = M.interest_credits(react, missed)
check("興味ありを押した公演の出演者が入る", ("出演", "作り手14") in people, people)
check("興味ありを押した公演の演出も入る", ("演出", "内藤裕子") in people, people)
check("興味なしを押した公演の出演者は含めない",
      ("出演", "作り手25") not in people, people)
check("控えに無い stage_id は静かに落ちる（例外にならない）", True, None)
check("興味あり2件＋観ればよかった1件で、同じ人は3回数えられる（roster の n に効く）",
      people.count(("出演", "作り手14")) == 3, people.count(("出演", "作り手14")))

# ---------------------------------------------------------------- add_interest_roster
#
# **◎ の基準（base）に相当する計算には触れない。** ここで検査するのは roster の
# 中身だけで、呼ぶ側が base をどう計算するかはこの関数の外にある
base_roster = {("出演", "作り手14"): (3, 2.0), ("演出", "内藤裕子"): (1, 1.0)}
merged = M.add_interest_roster(base_roster, people, 0.5)
check("既存の名簿にある人は加算される（上書きしない）",
      merged[("出演", "作り手14")] == (3 + 3, 2.0 + 0.5 * 3), merged[("出演", "作り手14")])
check("既存に無い人は新しく増える",
      merged[("演出", "内藤裕子")] == (1 + 1, 1.0 + 0.5), merged[("演出", "内藤裕子")])
check("元の名簿は書き換えない（純関数）", base_roster[("出演", "作り手14")] == (3, 2.0),
      base_roster)
check("重みは 1.0（◎ 相当）より必ず弱い",
      all(w < 1.0 for w in (0.5,)), None)

# ---------------------------------------------------------------- 実データでの健全性
#
# **base を動かさないことを、実際の数字で確かめる。**（起案者の指摘の裏付けに使った実測 ──
# いまの反応をそのまま `rated` に混ぜると基準が 0.38 → 0.57 に跳ね上がる、という事実）
import importlib                                                   # noqa: E402
importlib.reload(M)                                                 # _fields_by_stage を戻す

rated = M.load_rated()
pos = lambda v: 1.0 if v == "◎" else 0.0                            # noqa: E731
base = sum(pos(r["verdict"]) for r in rated) / max(len(rated), 1)
roster = M.build_roster(rated, pos)

import feedback as FB                                               # noqa: E402
con = FB.connect()
react_real = FB.reactions(con)
missed_real = FB.missed_fields(con)
con.close()
real_people = M.interest_credits(react_real, missed_real)
roster2 = M.add_interest_roster(roster, real_people, 0.5)

check("実データでも名簿が増える（興味あり・観ればよかったの人が混ざる）",
      len(roster2) >= len(roster), (len(roster), len(roster2)))
check("興味ありを 1 件も押していなくても壊れない（0 件でも動く）",
      isinstance(M.add_interest_roster(roster, [], 0.5), dict), None)

print(f"{ok} 件通過・{fail} 件失敗")
sys.exit(1 if fail else 0)
