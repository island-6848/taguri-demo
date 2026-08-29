#!/usr/bin/env python3
"""在庫が減るのかを、流入を入れて計算する。

## なぜ測り直すのか

[検証 037](../../docs/verification/037-first-day-guarantee.md) の追記 3 では、在庫を
固定したまま毎週 N 件出すシミュレーションで「週 15 件なら 7 週で空になる」と書いた。
**流入を入れていないことは限界として注記していたが、結論の数字はそのままだった。**
起案者の指摘「**逐次 月 260 件だか新着公演が追加されるんなら、たまっている在庫は
減らないのでは**」を受けて、流入を入れて計算する。

## 入れる数字（すべて実測）

- **在庫** ── 期待度が付いて初日がこれからの候補 108 件（初日までの日数の分布も実測値）
- **流入** ── 新規登録 **1 日 8 件 ＝ 週 56 件**（前日との差分を stage_id で突き合わせた）。
  企画書 5 章の「新規は月 260 件前後」とほぼ同じである（56 × 4.3 ＝ 241）
- **そのうち期待度が付く割合** ── **17%**（118／869）。したがって**流入は週 10 件**
- **流入の初日までの猶予** ── 実測した新規 8 件は最短 28 日・中央値 68 日だった。
  標本が小さいので、**7 日しか猶予が無い新着が混じる悲観の場合も計算する**

    python3 tools/stages/simulate_backlog.py
"""

from __future__ import annotations

import datetime
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REC = ROOT / "data" / "review" / "recommend2.json"
TODAY = datetime.date(2026, 8, 21)
INFLOW_PER_WEEK = 10          # 週 56 件の新規登録 × 期待度が付く 17%
NEW_LEAD_DAYS = [28, 43, 58, 68, 88, 104, 130, 189]   # 実測した新規 8 件の初日までの日数


def opening(period: str):
    m = re.findall(r"(20\d\d)/(\d{1,2})/(\d{1,2})", period or "")
    return datetime.date(*map(int, m[0])) if m else None


def stock() -> list[datetime.date]:
    d = json.loads(REC.read_text(encoding="utf-8"))
    return sorted(o for o in (opening(c["period"]) for c in d.get("scored_all", []))
                  if o and o >= TODAY)


def simulate(per_week: int, weeks: int, inflow: int, leads: list[int],
             pessimistic: float = 0.0):
    """毎週 per_week 件を初日が近い順に出す。未提示のまま初日を越えた件数を数える。

    pessimistic は「猶予が 7 日しかない新着」の割合。
    """
    queue = list(stock())
    missed = 0
    shown = 0
    log = []
    for w in range(weeks):
        day = TODAY + datetime.timedelta(days=7 * w)
        # その週の流入
        for i in range(inflow):
            if i < inflow * pessimistic:
                lead = 7
            else:
                lead = leads[i % len(leads)]
            queue.append(day + datetime.timedelta(days=lead))
        queue.sort()
        pick = queue[:per_week]
        del queue[:per_week]
        shown += len(pick)
        # 出せずに初日を越えたもの
        gone = [d for d in queue if d < day + datetime.timedelta(days=7)]
        for d in gone:
            queue.remove(d)
        missed += len(gone)
        log.append((w, len(pick), len(gone), len(queue)))
    return missed, shown, log


def main() -> int:
    print(f"在庫 {len(stock())} 件（期待度が付いて初日がこれから）／"
          f"流入 週 {INFLOW_PER_WEEK} 件（新規登録 週 56 件 × 17%）\n")
    for name, per, pess in [("週 15 件（1 セット）", 15, 0.0),
                            ("週 45 件（3 セット）", 45, 0.0),
                            ("週 15 件・悲観（新着の 2 割は猶予 7 日）", 15, 0.2),
                            ("週 30 件（2 セット）", 30, 0.0)]:
        missed, shown, log = simulate(per, 26, INFLOW_PER_WEEK, NEW_LEAD_DAYS, pess)
        empty = next((w for w, p, g, r in log if r == 0), None)
        print(f"■ {name}")
        print(f"   26 週で 未提示のまま初日を越えた: {missed} 件／出した {shown} 件")
        print(f"   在庫が空になる週: {empty if empty is not None else 'ならない'}"
              f"／26 週後の残り {log[-1][3]} 件")
        print("   残り在庫の推移（4 週ごと）: "
              + " → ".join(str(r) for w, p, g, r in log if w % 4 == 0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
