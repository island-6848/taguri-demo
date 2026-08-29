#!/usr/bin/env python3
"""興味ありからチケットを取ったと仮定して、次の週の推薦がどう変わるかを測る。

## なぜ仮定で測るのか

**購入確認メールの判定と抽出は 2026-04-08 で止まっている**（`data/tickets/performances.jsonl`
の最新がこの日付。[検証 022](../../docs/verification/022-where-reactions-go.md)）。実際に買うのを
待つと、買ってから観るまでが中央値 33 日（[検証 009](../../docs/verification/009-feedback-loop-preconditions.md)）で、
納期内に「次の週の推薦」を観測できない。**購入の信号を注入して、出力の差だけを測る。**

## 本物の DB には 1 行も書かない

`ratings.db` を複製し、複製に `owned=1` を立ててから推薦を出し直す。`--no-snapshot` で
`presented` にも入れない。**注入した反応が本物の履歴に混ざると、以降の測定がすべて汚れる。**

## 測る 4 つの筋

| | 仮定 | 何が分かるか |
|---|---|---|
| **A** | 現状（購入なし） | 比較の基準 |
| **B** | 追跡枠（興味あり）の 1 件を買った | 束の移動と、推薦枠の中身が動くか |
| **C** | 興味あり全件を買った（上限） | 購入をいくら積んでも中身が動かないかの確認 |
| **D** | B に加えて、観て ◎ を付けた | **中身が動くのはどの信号からか** |
| **E** | 推薦枠（未回答）の 1 件を買った | 席が 1 つ空いたとき、繰り上がる公演の質 |

    python3 tools/review/simulate_purchase.py
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import feedback as FB                          # noqa: E402
import measure_nets as M                       # noqa: E402
import recommend2 as R                         # noqa: E402

SRC = ROOT / "data" / "review" / "ratings.db"


def run(work: Path, tag: str, *, owned: list[str] = (), extra_rated=None) -> dict:
    """複製した DB に購入を注入して推薦を出し、結果を読んで返す。"""
    db = work / f"{tag}.db"
    shutil.copy(SRC, db)
    if owned:
        con = sqlite3.connect(db)
        for stage_id in owned:
            # **反応の行が無い公演もある**（推薦枠は未回答の公演を出す場所なので）。
            # 無ければ作る ── 購入は反応の有無に関係なく起きる。
            if not con.execute("SELECT 1 FROM reaction WHERE stage_id=?", (stage_id,)).fetchone():
                con.execute("INSERT INTO reaction (label, stage_id, owned, source, updated_at)"
                            " VALUES ('SIM', ?, 1, 'chat', '2026-08-20T00:00:00')", (stage_id,))
            else:
                con.execute("UPDATE reaction SET owned=1 WHERE stage_id=?", (stage_id,))
        con.commit()
        con.close()
    out = work / f"{tag}.json"
    FB.DB = db
    orig = M.load_rated
    if extra_rated is not None:
        M.load_rated = lambda: orig() + extra_rated          # noqa: B023
    try:
        sys.argv = ["recommend2", "--no-snapshot", "--out", str(out)]
        R.main()
    finally:
        M.load_rated = orig
    return json.loads(out.read_text(encoding="utf-8"))


def titles(d: dict, key: str = "recommend") -> list[str]:
    return [c["title"] for c in d.get(key, [])]


def diff(base: dict, other: dict, tag: str) -> None:
    a, b = titles(base), titles(other)
    sa = {c["title"]: c["total"] for c in base["recommend"]}
    sb = {c["title"]: c["total"] for c in other["recommend"]}
    moved = [k for k in sb if sa.get(k) != sb[k]]
    print(f"{tag}: 推薦枠の入れ替わり {len(set(b) - set(a))} 件"
          f"／順位が動いた {sum(1 for x, y in zip(a, b) if x != y)} 件"
          f"／スコアが動いた {len(moved)} 件")
    if set(b) - set(a):
        print(f"    入った: {sorted(set(b) - set(a))}／出た: {sorted(set(a) - set(b))}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="sim-purchase-") as tmp:
        work = Path(tmp)
        A = run(work, "A")
        track, rec = A["tracking"], A["recommend"]
        if not track or not rec:
            print("追跡枠か推薦枠が空なので測れない")
            return 1
        # **追跡枠の先頭は上演日がいちばん近い興味あり**（買うならここから買う）。
        one, top = track[0], rec[0]
        B = run(work, "B", owned=[str(one["stage_id"])])
        C = run(work, "C", owned=[str(c["stage_id"]) for c in track])
        # 観て ◎ を付けた場合。**名簿の正例は ◎ だけ**（検証 009）なので、
        # 購入した公演のクレジットをここで初めて名簿に入れる。
        extra = [{"key": "SIM", "title": one["title"], "date": "2026-09-01", "verdict": "◎",
                  "times": 1, "people": sorted(set(M.parse_credits(one["fields"]))), "venues": []}]
        D = run(work, "D", owned=[str(one["stage_id"])], extra_rated=extra)
        E = run(work, "E", owned=[str(top["stage_id"])])

        print("\n===== 比較 =====")
        print(f"買ったと仮定した公演: 追跡枠の先頭『{one['title']}』"
              f"（クレジット {len(set(M.parse_credits(one['fields'])))} 人）"
              f"／推薦枠の 1 位『{top['title']}』スコア {top['total']}")
        for tag, d in (("A 現状", A), ("B 追跡から 1 件買った", B),
                       ("C 興味あり全件を買った", C), ("D B に ◎ が付いた", D),
                       ("E 推薦枠の 1 位を買った", E)):
            print(f"{tag}: 推薦枠 {len(d['recommend'])}／追いかけている {len(d['tracking'])}"
                  f"／観る予定 {len(d['owned'])}／その他 {len(d['others'])}"
                  f"／スコアが正の候補 {d['n_scored']}"
                  f"／最上位 {d['recommend'][0]['total'] if d['recommend'] else 0}")
        print()
        for tag, d in (("B", B), ("C", C), ("D", D), ("E", E)):
            diff(A, d, tag)
        print(f"\nE で繰り上がって最下位に入った公演のスコア {E['recommend'][-1]['total']}"
              f"（買った公演は {top['total']}）── **空いた席に入るのは在庫の尾である**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
