#!/usr/bin/env python3
"""推薦を本番の利用者のデータで測る（docs/research/real-data-eval-plan.md）の、手元の集計。

復号した毎日の控え（backup.sql。docs/backup-restore.md）を、手元のメモリ上の SQLite に読み込んで数える。
本番の D1 は読まない（無料枠を使わない）。感想・メモの本文と名前は読まない（stage_id・答え・数だけ）。

  python3 tools/review/replay_eval.py backup.sql counts            # §8 の段 2: 何人・何件たまったか（毎週これだけを記録する）
  python3 tools/review/replay_eval.py backup.sql logged --owner U  # 答えたときに残した点での H1（利用者ごとの AUC）

- 「推薦の改善の分析に使わない」（app_setting の analysis_optout = '1'）を選んだ人は、どちらにも入れない。
- --owner で渡した利用者（持ち主）は除き、別の行に出す（dec-no-n1-evidence）。
- logged は、答えた画面ごとに分ける。開幕リマインド（reminder）が主な結果で、おすすめ（screen）は参考（§3 の偏り）。
- 判定（§1 の符号検定）は、--min-users（既定 1 人。起案者の指示 2026-10-18「利用者は1人からでも」）に満たなければ
  「まだ」と出す。人数が少ないうちの判定は、偶然の差を拾いやすい（§6 の目安は H1 で 15〜20 人、H5 で 30 人）。

  python3 tools/review/replay_eval.py backup.sql replay --index index.sql [--extra past.sql] [--step-days 7]

- replay（§3 の rolling origin と H5 の部品外し）: 日 t までの記録だけに切った写しで、Worker と同じ
  rankedGroups（cloudflare/scripts/replay_rank.js が node で呼ぶ）を動かし、t より後 step 日の答えを当てられたかを、
  利用者ごとの AUC（同じ区切りの中の組だけ）で見る。部品を 1 つずつ外した計算（REPLAY_ABLATIONS）とも比べる。
- 索引（--index）は build_recommend_index.py --output で手元の作業データから作る。控え（backup.sql）には索引が
  入っていない（backup_d1.DERIVED）。作業データの公演一覧は終わった公演も残すので、今日作った索引を日 t の
  候補として使い、日 t に始まっていない公演だけを候補にする（Worker の today = t + 1 日）。
"""
from __future__ import annotations

import argparse
import datetime
import json
import math
import sqlite3
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "cloudflare" / "migrations"
BRIDGE = ROOT / "cloudflare" / "scripts" / "replay_rank.js"
JST = datetime.timezone(datetime.timedelta(hours=9))
# cloudflare/src/screens/recommend.js の REPLAY_ABLATIONS と同じ（test_replay_eval が突き合わせる）
ABLATIONS = ("split", "expand", "spread", "gate", "impression")

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
        # ツアーのほかの会場へ写した答え（source が '…_tour'）は押した 1 回と同じ答えなので数えない（#110）
        if uid in out_ or (source or "").endswith("_tour"):
            continue
        screen = source or "screen"
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


# ---------------------------------------------------------------- replay（§3・H5）

STEP_DAYS = 7              # 区切りの長さ。§3 は 4 週間としていたが、記録がまだ数週間分なので 1 週間（§3 の追記 2026-10-18）
TIME_COLUMNS = ("updated_at", "created_at", "first_at")
KEEP_TABLES = {"users"}    # 切らない表（アカウントそのもの）


def jst_day(value) -> str | None:
    """記録の時刻を日本時間の日付に。'YYYY-MM-DD HH:MM:SS'（Python の画面が書いた日本時間）・ISO（Worker の UTC）・秒。"""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return datetime.datetime.fromtimestamp(value / 1000 if value > 1e11 else value, JST).date().isoformat()
    text = str(value)
    if "T" in text:
        try:
            t = datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return text[:10]
        return (t if t.tzinfo else t.replace(tzinfo=datetime.timezone.utc)).astimezone(JST).date().isoformat()
    return text[:10]


def build_base(backup: str, index: Path, extras: list[Path], path: Path) -> sqlite3.Connection:
    """全部の migrations の形の SQLite に、控えの記録（共通の列だけ）・索引・ほかの SQL を入れる。"""
    db = sqlite3.connect(path)
    for f in sorted(MIGRATIONS.glob("*.sql")):
        db.executescript(f.read_text(encoding="utf-8"))
    db.execute("PRAGMA foreign_keys=OFF")     # 表を名前の順に移すので、利用者の行より先に記録が入ることがある
    src = load(backup)
    for (table,) in src.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
        if not has_table(db, table):
            continue
        cols = [c for c in (r[1] for r in src.execute(f'PRAGMA table_info("{table}")')) if c in columns(db, table)]
        if not cols:
            continue
        names = ",".join(f'"{c}"' for c in cols)
        rows = src.execute(f'SELECT {names} FROM "{table}"').fetchall()
        db.executemany(f'INSERT OR REPLACE INTO "{table}" ({names}) VALUES ({",".join("?" * len(cols))})', rows)
    src.close()
    for f in [index, *extras]:
        db.executescript(Path(f).read_text(encoding="utf-8"))
    db.commit()
    return db


def answers_of(db: sqlite3.Connection) -> dict[str, list[tuple[str, str, bool, str]]]:
    """利用者ごとの答え（日付・公演・正例か・画面）。同じ公演への答えは最後のものだけ。分析から外れた人は入れない。"""
    out_ = opted_out(db)
    last: dict[tuple[str, str], tuple] = {}
    for uid, sid, interest, owned, source, updated in db.execute(
            "SELECT user_id, stage_id, interest, owned, source, updated_at FROM reaction "
            "WHERE interest IS NOT NULL OR owned=1 ORDER BY updated_at"):
        if uid in out_ or not jst_day(updated):
            continue
        screen = "reminder" if (source or "").startswith("reminder") else "other"
        last[(uid, str(sid))] = (jst_day(updated), str(sid), owned == 1 or interest in POSITIVE, screen)
    per = defaultdict(list)
    for (uid, _), row in last.items():
        per[uid].append(row)
    return {uid: sorted(rows) for uid, rows in per.items()}


def cut_copy(base: sqlite3.Connection, path: Path, day: str) -> None:
    """日 day（日本時間）より後に書かれた利用者の記録を消した写し。お気に入り（favourites）は時刻が無いので残る（§9）。"""
    cut = sqlite3.connect(path)
    base.backup(cut)
    cut.create_function("jst_day", 1, jst_day)
    for (table,) in cut.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall():
        cols = columns(cut, table)
        if table in KEEP_TABLES or "user_id" not in cols:
            continue
        for c in TIME_COLUMNS:
            if c in cols:
                cut.execute(f'DELETE FROM "{table}" WHERE jst_day("{c}") > ?', (day,))
    cut.commit()
    cut.close()


def bridge(path: Path, today: str, jobs: list[dict]) -> list[dict]:
    job = {"db": str(path), "today": today, "jobs": jobs}
    r = subprocess.run(["node", "--no-warnings", str(BRIDGE)], input=json.dumps(job, ensure_ascii=False),
                       capture_output=True, text=True, check=False)
    if r.returncode != 0:
        raise RuntimeError("replay_rank.js が失敗しました: " + r.stderr.strip()[-2000:])
    return json.loads(r.stdout)


def pair_wins(rows: list[tuple[bool, int | None]]) -> tuple[float, int]:
    """1 つの区切りの中の（正例, 負例）の組で、正例が上の数（同じ順位・どちらも圏外は半分）と組の数。"""
    key = lambda rank: -rank if rank is not None else -math.inf
    pos = [key(r) for p, r in rows if p]
    neg = [key(r) for p, r in rows if not p]
    return sum((x > y) + 0.5 * (x == y) for x in pos for y in neg), len(pos) * len(neg)


def wilcoxon_p(diffs: list[float]) -> float:
    """片側の Wilcoxon の符号順位検定（差が 0 より大きいか）。0 の差は落とし、同じ大きさは平均の順位。正確な分布。"""
    d = [x for x in diffs if x != 0]
    if not d:
        return 1.0
    order = sorted(range(len(d)), key=lambda i: abs(d[i]))
    rank2 = [0] * len(d)                     # 順位の 2 倍（同順位の平均を整数で持つ）
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and abs(d[order[j + 1]]) == abs(d[order[i]]):
            j += 1
        for k in range(i, j + 1):
            rank2[order[k]] = i + j + 2
        i = j + 1
    w = sum(r for r, x in zip(rank2, d) if x > 0)
    dist = {0: 1}
    for r in rank2:
        nxt = defaultdict(int)
        for s_, n in dist.items():
            nxt[s_] += n
            nxt[s_ + r] += n
        dist = nxt
    return sum(n for s_, n in dist.items() if s_ >= w) / 2 ** len(d)


def holm(ps: dict[str, float]) -> dict[str, float]:
    out, running = {}, 0.0
    for i, (k, p) in enumerate(sorted(ps.items(), key=lambda kv: kv[1])):
        running = max(running, min(1.0, (len(ps) - i) * p))
        out[k] = running
    return out


def replay(backup: str, index: Path, extras: list[Path], *, owner: str | None = None, min_users: int = 1,
           step_days: int = STEP_DAYS) -> dict:
    variants = {"base": {}, **{a: {a: True} for a in ABLATIONS}}
    with tempfile.TemporaryDirectory(prefix="replay-") as tmp:
        base = build_base(backup, index, extras, Path(tmp) / "base.sqlite")
        answers = answers_of(base)
        if not answers:
            return {"error": "答えの記録がありません"}
        first = min(rows[0][0] for rows in answers.values())
        last = max(rows[-1][0] for rows in answers.values())
        step = datetime.timedelta(days=step_days)
        # 最初の区切りは、最初に答えた日。それより前は、たぐりに記録が無いことが多い（D1 に移る前の記録は、移した日の時刻になる）
        t = datetime.date.fromisoformat(first)
        # 利用者 × 画面（reminder・other・all）× 計算 → [勝ち, 組]、区切りの数
        tally = defaultdict(lambda: [0.0, 0])
        windows = defaultdict(int)
        coverage = [0, 0]
        n_origins = 0
        per_origin = []           # 区切りごとの人数だけ（だれかは出さない）
        while t.isoformat() < last:
            lo, hi = t.isoformat(), (t + step).isoformat()
            targets = {uid: [r for r in rows if lo < r[0] <= hi] for uid, rows in answers.items()}
            targets = {u: rs for u, rs in targets.items() if len(rs) >= MIN_ANSWERS and any(r[2] for r in rs) and not all(r[2] for r in rs)}
            if targets:
                n_origins += 1
                cut = Path(tmp) / f"cut-{lo}.sqlite"
                cut_copy(base, cut, lo)
                jobs = [{"uid": u, "variant": v, "ablate": ab, "stages": sorted({r[1] for r in rs})}
                        for u, rs in sorted(targets.items()) for v, ab in variants.items()]
                got = bridge(cut, (t + datetime.timedelta(days=1)).isoformat(), jobs)
                ranks = {(o["uid"], o["variant"]): o["ranks"] for o in got}
                base_runs = [o for o in got if o["variant"] == "base"]
                per_origin.append({"t": lo, "users": len(targets), "answers": sum(len(rs) for rs in targets.values()),
                                   "with_ratings": sum(o.get("n_rated", 0) > 0 for o in base_runs),
                                   "with_recommendations": sum(o["n_ranked"] > 0 for o in base_runs)})
                cut.unlink()
                for u, rs in targets.items():
                    coverage[0] += sum(ranks[(u, "base")].get(r[1]) is not None for r in rs)
                    coverage[1] += len(rs)
                    for screen in ("reminder", "other", "all"):
                        sub = [r for r in rs if screen == "all" or r[3] == screen]
                        if not any(r[2] for r in sub) or all(r[2] for r in sub):
                            continue
                        windows[(u, screen)] += 1
                        for v in variants:
                            w, n = pair_wins([(r[2], ranks[(u, v)].get(r[1])) for r in sub])
                            tally[(u, screen, v)][0] += w
                            tally[(u, screen, v)][1] += n
            t += step
        base.close()
    auc_of = lambda u, sc, v: tally[(u, sc, v)][0] / tally[(u, sc, v)][1] if tally[(u, sc, v)][1] else None
    result = {"origins": n_origins, "step_days": step_days, "first_answer": first, "last_answer": last,
              "answers_ranked_share": round(coverage[0] / coverage[1], 3) if coverage[1] else None, "per_origin": per_origin}
    for screen in ("reminder", "other", "all"):
        users = sorted({u for (u, sc) in windows if sc == screen})
        others = [u for u in users if u != owner]
        base_auc = {u: auc_of(u, screen, "base") for u in users}
        vals = [base_auc[u] for u in others]
        enough = len(others) >= min_users and bool(others)
        entry = {"users": len(others), "windows": sum(windows[(u, screen)] for u in others),
                 "median_auc": sorted(vals)[len(vals) // 2] if vals else None,
                 "per_user_auc": [round(x, 3) for x in sorted(vals)],
                 "p_sign_H1": sign_test_p(sum(x > 0.5 for x in vals), sum(x < 0.5 for x in vals)) if enough else "まだ（人数が足りない）"}
        diffs = {a: [base_auc[u] - auc_of(u, screen, a) for u in others] for a in ABLATIONS}
        raw = {a: wilcoxon_p(d) for a, d in diffs.items()}
        adj = holm(raw)
        entry["H5"] = {a: {"median_diff": sorted(d)[len(d) // 2] if d else None, "users_better": sum(x > 0 for x in d),
                           "users_worse": sum(x < 0 for x in d),
                           "p_holm": round(adj[a], 4) if enough else "まだ（人数が足りない）"} for a, d in diffs.items()}
        if owner and owner in users:
            entry["owner"] = {"auc": base_auc[owner], **{f"diff_{a}": base_auc[owner] - auc_of(owner, screen, a) for a in ABLATIONS}}
        result[screen] = entry
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("backup", help="復号した控え（backup.sql）")
    ap.add_argument("what", choices=["counts", "logged", "replay"])
    ap.add_argument("--owner", help="持ち主の user_id（除いて別に出す）")
    ap.add_argument("--min-users", type=int, default=1,
                    help="判定を出す最少の人数（既定 1。§6 の目安は H1 で 15〜20 人、H5 で 30 人）")
    ap.add_argument("--index", type=Path, help="replay: 索引の SQL（build_recommend_index.py --output）")
    ap.add_argument("--extra", type=Path, action="append", default=[],
                    help="replay: ほかに読む SQL（deliver_past.py build の past_stage など。任意）")
    ap.add_argument("--step-days", type=int, default=STEP_DAYS, help="replay: 区切りの長さ（日）")
    a = ap.parse_args(argv)
    if a.what == "replay":
        if not a.index:
            ap.error("replay には --index が要ります")
        out = replay(a.backup, a.index, a.extra, owner=a.owner, min_users=a.min_users, step_days=a.step_days)
        json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
        print()
        return 0
    db = load(a.backup)
    out = counts(db, a.owner) if a.what == "counts" else logged(db, a.owner, a.min_users)
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
