#!/usr/bin/env python3
"""推薦を本番の利用者のデータで測る（docs/research/real-data-eval-plan.md）の、手元の集計。

復号した毎日の控え（backup.sql。docs/backup-restore.md）を、手元のメモリ上の SQLite に読み込んで数える。
本番の D1 は読まない（無料枠を使わない）。感想・メモの本文と名前は読まない（stage_id・答え・数だけ）。

  python3 tools/review/replay_eval.py backup.sql counts            # §8 の段 2: 何人・何件たまったか（毎週これだけを記録する）
  python3 tools/review/replay_eval.py backup.sql logged --owner U  # 答えたときに残した点での H1（利用者ごとの AUC）

- 「推薦の改善の分析に使わない」（app_setting の analysis_optout = '1'）を選んだ人は、どちらにも入れない。
- --owner で渡した利用者（持ち主）は除き、別の行に出す（dec-no-n1-evidence）。
- logged は、答えた画面ごとに分ける。開幕リマインド（reminder）が主な結果で、おすすめ（screen）は参考（§3 の偏り）。
- 判定（§1 の符号検定）は、§6 の人数がそろうまで出さない（--min-users に満たなければ「まだ」と出す）。
- 過去のある日の候補を組み直す再生（§3 の rolling origin と H5 の部品外し）は、Worker の recommend.js を node で
  呼ぶ橋がまだ無い（公演の索引を日ごとに組み直す材料が要る）。ここでは答えたときに残した点だけを使う。
"""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
import sys
from collections import defaultdict

POSITIVE = {1, 2}          # 興味あり・行けない（購入済は owned=1 で別に正例にする）
MIN_ANSWERS = 3            # 1 人の答えがこれ未満なら、その人の AUC は数えない（§3）


def load(path: str) -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    with open(path, encoding="utf-8") as f:
        db.executescript(f.read())
    return db


def has_table(db: sqlite3.Connection, name: str) -> bool:
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def columns(db: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in db.execute(f"PRAGMA table_info({table})")}


def opted_out(db: sqlite3.Connection) -> set[str]:
    if not has_table(db, "app_setting"):
        return set()
    return {r[0] for r in db.execute("SELECT user_id FROM app_setting WHERE key='analysis_optout' AND value='1'")}


def counts(db: sqlite3.Connection, owner: str | None) -> dict:
    out_ = opted_out(db)
    users = defaultdict(lambda: {"answers": 0, "with_score": 0, "reminder": 0, "shown_days": 0})
    has_score = "score" in columns(db, "reaction")
    for uid, interest, owned, source, score in db.execute(
            f"SELECT user_id, interest, owned, source, {'score' if has_score else 'NULL'} FROM reaction "
            "WHERE interest IS NOT NULL OR owned=1"):
        if uid in out_:
            continue
        u = users[uid]
        u["answers"] += 1
        u["with_score"] += score is not None
        u["reminder"] += (source or "").startswith("reminder")
    if has_table(db, "rec_shown"):
        for uid, n in db.execute("SELECT user_id, count(*) FROM rec_shown GROUP BY user_id"):
            if uid not in out_:
                users[uid]["shown_days"] += n
    others = {k: v for k, v in users.items() if k != owner}
    return {
        "users": len(others),
        "users_10_answers": sum(v["answers"] >= 10 for v in others.values()),
        "answers": sum(v["answers"] for v in others.values()),
        "answers_with_score": sum(v["with_score"] for v in others.values()),
        "answers_reminder": sum(v["reminder"] for v in others.values()),
        "shown_rows": sum(v["shown_days"] for v in others.values()),
        "opted_out": len(out_),
        "owner": users.get(owner) if owner else None,
    }


def auc(pos: list[float], neg: list[float]) -> float | None:
    """正例が負例より上に来る割合（同点は半分）。どちらかが無ければ None。"""
    if not pos or not neg:
        return None
    win = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return win / (len(pos) * len(neg))


def sign_test_p(wins: int, losses: int) -> float:
    """片側の符号検定（中央値が 0.5 より上か）。同点（0.5 ちょうど）は数えない。"""
    n = wins + losses
    return sum(math.comb(n, k) for k in range(wins, n + 1)) / 2 ** n if n else 1.0


def logged(db: sqlite3.Connection, owner: str | None, min_users: int) -> dict:
    if "score" not in columns(db, "reaction"):
        return {"error": "この控えには reaction.score がありません（migrations/0029 より前の控え）"}
    out_ = opted_out(db)
    per = defaultdict(lambda: ([], []))
    for uid, interest, owned, source, score in db.execute(
            "SELECT user_id, interest, owned, source, score FROM reaction WHERE score IS NOT NULL AND (interest IS NOT NULL OR owned=1)"):
        if uid in out_:
            continue
        screen = (source or "screen").removesuffix("_tour")
        pos = owned == 1 or interest in POSITIVE
        per[(uid, screen)][0 if pos else 1].append(score)
    result = {}
    for screen in sorted({s for _, s in per}):
        rows = {uid: auc(p, n) for (uid, s), (p, n) in per.items() if s == screen and len(p) + len(n) >= MIN_ANSWERS}
        others = [a for uid, a in rows.items() if uid != owner and a is not None]
        wins, losses = sum(a > 0.5 for a in others), sum(a < 0.5 for a in others)
        entry = {"users": len(others), "median_auc": sorted(others)[len(others) // 2] if others else None,
                 "owner_auc": rows.get(owner) if owner else None}
        entry["p_sign"] = sign_test_p(wins, losses) if len(others) >= min_users else "まだ（人数が足りない）"
        result[screen] = entry
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("backup", help="復号した控え（backup.sql）")
    ap.add_argument("what", choices=["counts", "logged"])
    ap.add_argument("--owner", help="持ち主の user_id（除いて別に出す）")
    ap.add_argument("--min-users", type=int, default=15, help="判定を出す最少の人数（§6。H1 は 15〜20 人）")
    a = ap.parse_args(argv)
    db = load(a.backup)
    out = counts(db, a.owner) if a.what == "counts" else logged(db, a.owner, a.min_users)
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
