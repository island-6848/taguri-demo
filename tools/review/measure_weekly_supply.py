#!/usr/bin/env python3
"""「週 10〜15 件」の分母を測る（V8）。

    python3 tools/review/measure_weekly_supply.py

## 何を測るのか ── 在庫ではなく、週あたりの供給である

企画書は**出す件数**を「週 10〜15 件」と書いているが、これは「運用が週 1 回 3 分だから
逆算した」暫定値で、**供給の側から確かめていない。** 在庫（いま点が付いている候補の総数）
なら 1 週ぶんの枠は必ず埋まるので、**確かめるべきは「毎週、新しく何件が現れるか」**である。

## 初報の日は記録に無いので、初日で数える

**新しく現れた日（初報）は持っていない。** 候補の一覧は月に 1 回取り直すだけで、
「いつ載ったか」を残していない。そこで**出ていく側で数える** ── 定常状態では
「新しく入る件数」と「初日を迎えて対象から外れる件数」は等しい。初日は候補の
`period` にあるので、**初日の週ごとの件数がそのまま週あたりの供給になる。**

**遠い週は数えられない。** 先の公演はまだ一覧に載っていない（[検証 025](
../../docs/verification/025-venue-coverage.md) の「掲載漏れではなく掲載の遅れ」）ので、
週を先に取るほど件数が落ちる。**判定に使うのは近い 6 週だけ**にする ── そこは
載り切っている範囲である。

## 束ごとに分けて出す

企画書は「件数を担っているのは網 C で、精度を担っているのは網 B」と書いている
（[検証 030](../../docs/verification/030-own-knowledge-claim.md)）。**その配分が
週あたりでどうなっているかも、同じ計算で出る。**
"""

from __future__ import annotations

import collections
import datetime as dt
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "review"))
import recommend2 as RC2                                            # noqa: E402

SRC = ROOT / "data" / "review" / "recommend2.json"
NEAR = 6                      # 判定に使う週数（載り切っている範囲）
CLAIM = (10, 15)              # 企画書が書いている件数


def start(c: dict):
    s = RC2.period_start(c.get("period") or "")
    return dt.date.fromisoformat(s) if s else None


def per_week(rows: list, today: dt.date, near: int = NEAR) -> dict:
    """初日の週ごとの件数。**今週を 0 とする。**"""
    ws: collections.Counter = collections.Counter()
    nodate = 0
    for c in rows:
        s = start(c)
        if not s:
            nodate += 1
            continue
        ws[(s - today).days // 7] += 1
    near_v = [ws[w] for w in range(near)]
    return {"n": len(rows), "nodate": nodate, "weeks": ws, "near": near_v,
            "median": st.median(near_v) if near_v else 0,
            "mean": round(sum(near_v) / len(near_v), 1) if near_v else 0,
            "past": sum(v for k, v in ws.items() if k < 0)}


def main() -> int:
    today = dt.date.today()
    d = json.loads(SRC.read_text(encoding="utf-8"))
    ranked, favs = d["ranked"], d["favourites"]
    b_on = [c for c in ranked if (c.get("b") or 0) > 0]
    c_only = [c for c in ranked if (c.get("b") or 0) == 0 and (c.get("c") or 0) > 0]

    print(f"{today} 時点／候補 {d['n_cand']} 件・点が付いた候補 {d['n_scored']} 件")
    print(f"（効かせ方は既定 ── 画面のつまみは点の計算より後に掛かるので、"
          f"ここで測るのは実測の重みそのままの形である）\n")
    rows = (("点が付いた候補（全体）", ranked), ("うち名簿（網 B）が効いた", b_on),
            ("内容（網 C）だけ", c_only), ("お気に入りの新着（網 A）", favs))
    out = {}
    for name, rs in rows:
        r = per_week(rs, today)
        out[name] = r
        wk = " ".join(f"{r['weeks'][w]:>3d}" for w in range(13))
        print(f"{name}")
        print(f"  {r['n']:3d} 件（初日が読めない {r['nodate']}／初日が過ぎた {r['past']}）")
        print(f"  週ごと（今週から 13 週）: {wk}")
        print(f"  近い {NEAR} 週: 中央値 {r['median']}／平均 {r['mean']}\n")

    total = out["点が付いた候補（全体）"]
    lo, hi = CLAIM
    verdict = ("上限まで供給がある" if total["mean"] >= hi else
               "下限は満たすが、上限には届かない" if total["mean"] >= lo else
               f"下限の {lo} 件にも届かない")
    print(f"判定: 供給は週あたり {min(total['near'])}〜{max(total['near'])} 件"
          f"（近い {NEAR} 週の平均 {total['mean']} 件）。"
          f"企画書の「週 {lo}〜{hi} 件」は **{verdict}**。")
    print(f"  いま出していない在庫は {total['n'] - 15} 件 ── **枠は埋まるが、"
          f"毎週 15 件が新しくなるわけではない。**")
    print(f"  件数を担っているのは内容（網 C）で週 {out['内容（網 C）だけ']['mean']} 件、"
          f"名簿（網 B）は週 {out['うち名簿（網 B）が効いた']['mean']} 件である。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
