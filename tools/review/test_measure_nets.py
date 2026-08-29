#!/usr/bin/env python3
"""クレジットの読み取り（`measure_nets.parse_credits` / `_names`）の検査。

    python3 tools/review/test_measure_nets.py

起案者の報告（2026-08-26）── 「The show! マレーネ…のやつでポスターと出演者を手で入れる、
のところで名簿に 4 人書いているのに、3 人しか反映されていないのはなぜ？」。

**「演出」「脚本」欄に【役職】タグを付けた名前を書くと、名前ごと消えていた。**
`_BRACKET` はスタッフ欄の「【役職】名前」を扱うために足したものだが、出演・脚本・演出の
3 欄は `_names()` を直接呼ぶので通らず、`_ROLE_PREFIX`（括弧の付かない役職しか剥がせない）
が素通しした角括弧が、名前を消す安全策（`"[【】［］《》]"` を含む語は捨てる）に当たって
名前ごと落ちていた。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "review"))
sys.path.insert(0, str(ROOT / "tools" / "taguri"))
import measure_nets as MN                                          # noqa: E402
import app as APP                                                  # noqa: E402

ok = fail = 0


def check(name: str, cond: bool, got=None) -> None:
    global ok, fail
    if cond:
        ok += 1
        print(f"  OK  {name:<52} {got if got is not None else ''}")
    else:
        fail += 1
        print(f"  NG  {name:<52} ← {got!r}")


# ---------------------------------------------------------------- 実際に起きた例
# 「The Show！「マレーネ・ディートリヒ」東京公演」で本人が入れた 4 名（前田美波里・
# 作り手24・笹部博司・赤坂麻里）。演出と脚本は【】タグ付きで書いてある。
REAL = {"出演": "前田美波里\n作り手24（劇団2）",
        "演出": "【演出】 笹部博司",
        "脚本": "【台本】 笹部博司",
        "スタッフ": "【振付・ステージング】 赤坂麻里"}

check("【演出】タグ付きの名前が消えずに読める",
      MN._names(REAL["演出"]) == ["笹部博司"], MN._names(REAL["演出"]))
check("【台本】タグ付きの名前も読める（役職の語彙に無い語でも）",
      MN._names(REAL["脚本"]) == ["笹部博司"], MN._names(REAL["脚本"]))
check("スタッフ欄の【役職】書式は元から読めていた（回帰していないことの確認）",
      MN._names("赤坂麻里") == ["赤坂麻里"])

got = MN.parse_credits(REAL)
people = {p for _r, p in got}
check("4 人全員が名簿に入る", people == {"前田美波里", "作り手24", "笹部博司", "赤坂麻里"},
      sorted(people))
check("演出と脚本を兼ねる人は、役職ごとに別の組として残る（1 人が消えたことにしない）",
      ("演出", "笹部博司") in got and ("脚本", "笹部博司") in got, got)

# ---------------------------------------------------------------- 表示する人数
# **数えるのは人であって、(役職, 人) の組ではない。** 演出と脚本を兼ねる 1 人を
# 2 人と数えると、「4 名入れたのに 5 名と出る」という別の食い違いになる。
n = APP.hand_credit_count(REAL)
check("「◯名」は人数で数える（4 人 → 4、5 ではない）", n == 4, n)

# ---------------------------------------------------------------- 壊していないことの確認
check("普通の名前（角括弧なし）はそのまま読める",
      MN._names("前田美波里") == ["前田美波里"])
check("役職の語彙そのものは名前として読まない",
      MN._names("演出") == [])
check("角括弧の中身だけ（名前が続かない）は読まない",
      MN._names("【演出】") == [])
check("既存のスタッフ欄の複数【役職】名前も崩れていない",
      MN.parse_credits({"スタッフ": "【美術】山田太郎\n【照明】鈴木一郎"})
      == [("照明", "鈴木一郎"), ("美術", "山田太郎")])

print(f"{ok} 件通過・{fail} 件失敗")
sys.exit(1 if fail else 0)
