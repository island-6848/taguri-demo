"""storyline.panel on hand-made rated rows: the reference for src/screens/storyline.js
(test/storyline.test.js).

    python3 test/screens/storyline_fixture.py

The rows are fixed (a seeded random.Random, no today()): storyline's "直近 1 年" is measured
back from the latest session, not from today, so the output does not move with the clock.
"""
from __future__ import annotations

import datetime
import json
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def row(key, title, date, people, venues=()):
    return {"key": key, "title": title, "date": date, "verdict": "◎",
            "people": sorted({tuple(p) for p in people}), "venues": list(venues)}


def world_rows(rng, prefix, names, start, days, n, per=(3, 6), roles=("出演", "演出", "脚本")):
    """n 回の観劇。名前は時期によって入れ替わる（線が途中で入って途中で抜ける）。"""
    out = []
    d0 = datetime.date.fromisoformat(start)
    for k in range(n):
        d = d0 + datetime.timedelta(days=int(k * days / n) + rng.randrange(0, 9))
        # 時期に応じて出てくる人の窓をずらす
        lo = int(k * (len(names) - per[1]) / max(n - 1, 1))
        pool = names[max(0, lo - 2): lo + per[1] + 2]
        ms = rng.sample(pool, min(len(pool), rng.randint(*per)))
        ppl = [(rng.choice(roles), m) for m in ms] + [("出演", f"{prefix}端役{k}")]
        out.append(row(f"{prefix}{k}#{d}", f"{prefix}の作品 {k} <{'夜' * (k % 3)}> & \"長い題名のつづき\"",
                       d.isoformat(), ppl, ["劇場"]))
    return out


def big():
    rng = random.Random(20261014)
    A = [f"甲{i:02d}" for i in range(14)]
    B = [f"乙{i:02d}" for i in range(9)]
    C = [f"丙{i}" for i in range(4)]
    rows = world_rows(rng, "ミュ", A, "2022-01-08", 1100, 26)
    rows += world_rows(rng, "現代", B, "2023-06-01", 900, 14, per=(3, 5))
    rows += world_rows(rng, "古典", C, "2024-02-01", 300, 5, per=(2, 3))
    # 同じ日に 2 演目（座組を共有する）── 1 つのセッションにまとまる
    rows.append(row("デカ1#2024-04-21", "デカローグ 1", "2024-04-21", [("出演", m) for m in B[2:7]]))
    rows.append(row("デカ3#2024-04-21", "デカローグ 3", "2024-04-21", [("出演", m) for m in B[3:8]]))
    # 同じ日の別の世界（共有しない）── まとめない
    rows.append(row("別#2024-04-21", "別の世界の同じ日", "2024-04-21", [("出演", m) for m in A[5:9]]))
    # 日付が無い・人が無い・壊れた日付は数えない
    rows.append(row("日付なし#", "日付なし", "", [("出演", A[0])]))
    rows.append(row("壊れ#", "壊れた日付", "2024-02-30", [("出演", A[0])]))
    rows.append(row("無人#2024-05-01", "人なし", "2024-05-01", []))
    # 1 回だけの人（線にならない）
    rows.append(row("一度#2023-01-01", "一度だけ", "2023-01-01", [("出演", "一度きり"), ("出演", A[1])]))
    rng.shuffle(rows)
    return rows


def small():
    P = ["あ", "い", "う", "え"]
    return [row(f"s{k}#2025-0{k + 1}-10", f"小さな作品{k}", f"2025-0{k + 1}-10",
                [("出演", P[j]) for j in range(4) if (k + j) % 3]) for k in range(7)]


def one_recent():
    """直近 1 年に束があるのは片方だけ。"""
    rows = [row(f"x{k}#2021-0{k + 1}-01", f"古い流れ{k}", f"2021-0{k + 1}-01",
                [("出演", "古A"), ("出演", "古B"), ("演出", "古C")]) for k in range(5)]
    rows += [row(f"y{k}#2024-0{k + 1}-01", f"新しい流れ{k}", f"2024-0{k + 1}-01",
                 [("出演", "新A"), ("出演", "新B")]) for k in range(4)]
    return rows


def main():
    sys.path[:0] = [str(REPO / "tools" / "taguri"), str(REPO / "tools" / "review")]
    import storyline as SL
    few = [row(f"f{k}#2024-01-0{k + 1}", "少", f"2024-01-0{k + 1}", [("出演", "誰か")]) for k in range(3)]
    cases = []
    for rated, mt in ((big(), 4), (big(), 3), (big(), 6), (small(), 4), (small(), 2), (one_recent(), 4),
                      ([], 4), (few, 4)):
        cases.append({"rated": rated, "min_times": mt, "html": SL.panel(rated, mt)})
    print(json.dumps({"cases": cases}, ensure_ascii=False))


if __name__ == "__main__":
    main()
