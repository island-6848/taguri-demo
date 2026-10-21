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
import re
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
ABLATIONS = ("split", "expand", "spread", "gate", "impression", "rollup")
# 足して試す部品（H6）: 画面ではまだ動いていない部品を効かせた計算と比べる（ctx.ablate の try_<名前>）。
# affil: 所属（劇団）から値の無い人を推し量る（cloudflare/src/recommend.js withAffil、dec-affil-reco）
TRIALS = ("affil",)

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


GRADE = re.compile(r"^(\d{1,2})/(\d{1,2})$")


def graded(verdict) -> bool:
    """recommend.gradeOf と同じ: ◎○△× か「n/m」（2〜11 段）。"""
    if verdict in ("◎", "○", "△", "×"):
        return True
    m = GRADE.match(str(verdict or ""))
    return bool(m) and 2 <= int(m[2]) <= 11 and 1 <= int(m[1]) <= int(m[2])


def materials(backup: str, index: Path, extras: list[Path], today: str) -> dict:
    """今の記録のうち、推薦の材料になれている数（ratedWorks と同じ条件。集計だけで、作品名は出さない）。"""
    with tempfile.TemporaryDirectory(prefix="materials-") as tmp:
        db = build_base(backup, index, extras, Path(tmp) / "base.sqlite")
        ver = (db.execute("SELECT v FROM rec_meta WHERE k='current'").fetchone() or [None])[0]
        rec = {sid: json.loads(p) for sid, p in db.execute("SELECT stage_id, people FROM rec_people WHERE ver=?", (ver,))}
        past = {sid: json.loads(p) for sid, p in db.execute("SELECT stage_id, people FROM past_stage")} if has_table(db, "past_stage") else {}
        out_ = opted_out(db)
        c = defaultdict(int)
        for uid, verdict, sid, first, note in db.execute(
                "SELECT user_id, verdict, stage_id, first_date, note_impression FROM works"):
            if uid in out_:
                continue
            c["records"] += 1
            if not graded(verdict):
                continue
            c["rated"] += 1
            if (first or "") > today:
                c["rated_future"] += 1
                continue
            if not sid:
                c["rated_unlinked"] += 1
                continue
            people = rec.get(sid) if sid in rec else past.get(sid)
            c["linked_index" if sid in rec else "linked_past" if sid in past else "linked_missing"] += 1
            names = [p for p in people or [] if not str(p[0]).startswith("#")]
            kinds = [p for p in people or [] if str(p[0]).startswith("#") and p[0] in ("#形式", "#原作", "#翻訳", "#原作の国", "#題材", "#ジャンル")]
            c["with_names"] += bool(names)
            c["with_kinds"] += bool(kinds)
            c["with_note"] += bool((note or "").strip())
            c["with_note_and_kinds"] += bool((note or "").strip()) and bool(kinds)
        db.close()
    return dict(c)


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


# ---------------------------------------------------------------- H3（§2・#114）
# 「気になったか」（H1 の答え）と「観てよかったか」を分ける。観る前に記録した点（reaction.score、答えたときの点）と、
# 観たあとの本人の評価（works.verdict）を公演で結び、利用者ごとに Kendall の τ-b を出す。
# 観なかった公演は満足の負例にしない（評価の無い公演は入れない）。推薦の計算は変えない（測るだけ）。
MARKS = {"◎": 1.0, "○": 2 / 3, "△": 1 / 3, "×": 0.0}


def grade_point(verdict) -> float | None:
    """評価を 0〜1 に（◎○△× と「n/m」。graded と同じ範囲）。τ は 1 人の中の並びだけを見るので、目盛りの違いは問わない"""
    if verdict in MARKS:
        return MARKS[verdict]
    if not graded(verdict):
        return None
    m = GRADE.match(str(verdict))
    return (int(m[1]) - 1) / (int(m[2]) - 1)
MIN_H3 = 3                 # 1 人の結べた公演がこれ未満なら、その人の τ は数えない


def kendall_tau_b(xs: list[float], ys: list[float]) -> float | None:
    conc = disc = tx = ty = 0
    for i in range(len(xs)):
        for j in range(i + 1, len(xs)):
            dx, dy = xs[i] - xs[j], ys[i] - ys[j]
            if dx == 0 and dy == 0:
                continue
            if dx == 0:
                tx += 1
            elif dy == 0:
                ty += 1
            elif (dx > 0) == (dy > 0):
                conc += 1
            else:
                disc += 1
    den = math.sqrt((conc + disc + tx) * (conc + disc + ty))
    return (conc - disc) / den if den else None


def h3(db: sqlite3.Connection, owner: str | None, min_users: int) -> dict:
    """観る前の点（観た日より前の答えの score）と観たあとの評価の τ。欠測と、答えた公演に偏る度合いも出す。"""
    if "score" not in columns(db, "reaction"):
        return {"error": "この控えには reaction.score がありません（migrations/0029 より前の控え）"}
    out_ = opted_out(db)
    before: dict[tuple[str, str], list[tuple[str, float, bool]]] = defaultdict(list)
    for uid, sid, score, updated, interest, owned, source in db.execute(
            "SELECT user_id, stage_id, score, updated_at, interest, owned, source FROM reaction WHERE score IS NOT NULL ORDER BY updated_at"):
        if uid in out_ or (source or "").endswith("_tour"):
            continue
        before[(uid, str(sid))].append((jst_day(updated) or "", float(score), owned == 1 or interest in POSITIVE))
    per = defaultdict(lambda: ([], []))
    c = defaultdict(int)
    for uid, sid, verdict, first in db.execute(
            "SELECT user_id, stage_id, verdict, first_date FROM works WHERE verdict IS NOT NULL AND verdict<>''"):
        if uid in out_ or grade_point(verdict) is None:
            continue
        c["rated"] += 1
        if not sid:
            c["no_stage"] += 1
            continue
        # 観た日（first_date）より前に答えた点のうち、いちばん後のものが「観る前」。観た日のあとの点は、観たことを知っている
        got = next((b for b in reversed(before.get((uid, str(sid)), [])) if first and b[0] and b[0] < str(first)[:10]), None)
        if not got:
            c["no_score_before"] += 1
            continue
        c["paired"] += 1
        c["paired_after_positive"] += got[2]
        per[uid][0].append(got[1])
        per[uid][1].append(grade_point(verdict))
    taus = {u: kendall_tau_b(x, y) for u, (x, y) in per.items() if len(x) >= MIN_H3}
    others = [t for u, t in taus.items() if u != owner and t is not None]
    enough = len(others) >= min_users and bool(others)
    return {"rated": c["rated"], "paired": c["paired"],
            # 欠測: 公演につながっていない・観る前の点が無い。結べたうち、興味あり・購入済と答えていた割合（選んで観た偏り）
            "missing": {"no_stage": c["no_stage"], "no_score_before": c["no_score_before"]},
            "paired_after_positive_share": round(c["paired_after_positive"] / c["paired"], 3) if c["paired"] else None,
            "users": len(others), "median_tau": round(sorted(others)[len(others) // 2], 3) if others else None,
            "per_user_tau": [round(t, 3) for t in sorted(others)],
            "p_sign_H3": sign_test_p(sum(t > 0 for t in others), sum(t < 0 for t in others)) if enough else "まだ（人数が足りない）",
            **({"owner_tau": taus.get(owner)} if owner and owner in taus else {})}


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


INDEX_TABLES = ("rec_stage", "rec_people", "rec_credit", "rec_affil")


def index_split(seen: dict | None, day: str, stage_ids: set[str] = frozenset()) -> dict:
    """索引の公演を、日 day に載っていたかで分ける（#72）。seen は d1/index-hashes.json（build_recommend_index.seen_dates）。

    later: day より後に初めて載った公演（再生で落とす）。changed: day には載っていたが、そのあと中身が変わった公演の数
    （今の中身で測るので、少し当たって見えるかもしれない）。unknown: day が控えを始めた日より前（載った日が分からない）。
    stage_ids: 写しの索引の公演。seen に無い公演（作業データにはあるが、まだ D1 に入れていない）も落とす。"""
    if not seen or not seen.get("_seen"):
        return {"later": set(), "changed": 0, "unknown": True}
    since = seen.get("_seen_since") or ""
    later, changed = set(), 0
    for sid, (first, last, *_rest) in seen["_seen"].items():
        if first > day and first != since:     # 控えを始めた日に入っていた公演は、それより前から載っていたかもしれない
            later.add(str(sid))
        elif last > day:
            changed += 1
    later |= {sid for sid in stage_ids if sid not in seen["_seen"]}
    return {"later": later, "changed": changed, "unknown": day < since}


def declared_at(db: sqlite3.Connection, day: str) -> None:
    """日 day より後に書き換えたお気に入り（app_setting の declared）を、day までに足した名前だけに戻す（#72）。
    名前ごとの足した時刻は declared_at（lists.favouriteAction）。時刻の無い名前は、時刻を控える前に足したので残す。
    day より後に外した名前は戻せない（declared_at からも消える）。"""
    if not has_table(db, "app_setting"):
        return
    rows = db.execute("SELECT user_id, value, updated_at FROM app_setting WHERE key='declared'").fetchall()
    for uid, value, updated in rows:
        if (jst_day(updated) or "") <= day:
            continue
        at = db.execute("SELECT value FROM app_setting WHERE user_id=? AND key='declared_at'", (uid,)).fetchone()
        try:
            dec, stamps = json.loads(value or "{}"), json.loads(at[0]) if at else {}
        except ValueError:
            continue
        kept = {k: [n for n in names if (jst_day(stamps.get(f"{k}\t{n}")) or "") <= day]
                for k, names in dec.items() if isinstance(names, list)}
        if any(kept.values()):
            db.execute("UPDATE app_setting SET value=?, updated_at=? WHERE user_id=? AND key='declared'",
                       (json.dumps(kept, ensure_ascii=False), day, uid))


def cut_copy(base: sqlite3.Connection, path: Path, day: str, later: set[str] = frozenset()) -> None:
    """日 day（日本時間）より後に書かれた利用者の記録と、day より後に載った索引の公演（later）を消した写し。
    お気に入り（app_setting の declared）は、day までに足した名前に戻す（declared_at）。古い favourites の表は時刻が無いので残る（§9）。"""
    cut = sqlite3.connect(path)
    base.backup(cut)
    if later:
        ids = sorted(later)
        for table in INDEX_TABLES:
            if has_table(cut, table):
                for i in range(0, len(ids), 500):
                    part = ids[i:i + 500]
                    cut.execute(f'DELETE FROM "{table}" WHERE stage_id IN ({",".join("?" * len(part))})', part)
    cut.create_function("jst_day", 1, jst_day)
    declared_at(cut, day)
    for (table,) in cut.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall():
        cols = columns(cut, table)
        if table in KEEP_TABLES or "user_id" not in cols:
            continue
        for c in TIME_COLUMNS:
            if c in cols:
                cut.execute(f'DELETE FROM "{table}" WHERE jst_day("{c}") > ?', (day,))
    cut.commit()
    cut.close()


# ---------------------------------------------------------------- 学習曲線（#103）
# 「評価が増えるほど当たるか」を、同じ区切り・同じ後の答え・同じ索引のまま、日 t までの評価を古いほうから k 件だけ
# 残して測る。索引の変化（カタログの更新）と評価の増え方を切り分けるため、区切りごとに索引は変えない。
CURVE = (1, 2, 5, 10, 20)


def rated_counts(db: sqlite3.Connection) -> dict[str, int]:
    return {uid: n for uid, n in db.execute(
        "SELECT user_id, count(*) FROM works WHERE verdict IS NOT NULL AND verdict<>'' GROUP BY user_id")}


def keep_oldest(path: Path, k: int) -> None:
    """写しの評価を、利用者ごとに古いほう（評価した時刻の順）から k 件だけ残す。評価の無い記録はそのまま"""
    db = sqlite3.connect(path)
    gone = db.execute(
        "SELECT user_id, work_key FROM (SELECT user_id, work_key, row_number() OVER (PARTITION BY user_id "
        "ORDER BY coalesce(rated_at, updated_at), work_key) AS i FROM works WHERE verdict IS NOT NULL AND verdict<>'') "
        "WHERE i > ?", (k,)).fetchall()
    db.executemany("DELETE FROM works WHERE user_id=? AND work_key=?", gone)
    if has_table(db, "work_piece"):
        db.executemany("DELETE FROM work_piece WHERE user_id=? AND work_key=?", gone)
    db.commit()
    db.close()


def curve_summary(tally: dict, ks: list) -> list[dict]:
    """k ごとの AUC の中央値・人数と、最小の k と比べて良くなった人・悪くなった人（符号検定の p）。
    tally: (uid, k) -> [勝ち, 組, 入っていた答え, 答え]。k=None は全部の評価"""
    auc = {key: w / n for key, (w, n, _h, _a) in tally.items() if n}
    out = []
    first = ks[0]
    for k in ks:
        users = sorted(u for (u, kk) in auc if kk == k)
        vals = sorted(auc[(u, k)] for u in users)
        both = [u for u in users if (u, first) in auc]
        better = sum(auc[(u, k)] > auc[(u, first)] for u in both)
        worse = sum(auc[(u, k)] < auc[(u, first)] for u in both)
        hit = sum(v[2] for (u, kk), v in tally.items() if kk == k)
        ans = sum(v[3] for (u, kk), v in tally.items() if kk == k)
        if not users:
            continue
        out.append({"k": "all" if k is None else k, "users": len(users),
                    "median_auc": round(vals[len(vals) // 2], 3) if vals else None,
                    "answers_ranked_share": round(hit / ans, 3) if ans else None,
                    "better_than_first": better, "worse_than_first": worse,
                    "p_sign": sign_test_p(better, worse) if k != first and better + worse else None})
    return out


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
           step_days: int = STEP_DAYS, seen: dict | None = None, curve: tuple | None = None) -> dict:
    variants = {"base": {}, **{a: {a: True} for a in ABLATIONS}, **{f"try_{t}": {f"try_{t}": True} for t in TRIALS}}
    with tempfile.TemporaryDirectory(prefix="replay-") as tmp:
        base = build_base(backup, index, extras, Path(tmp) / "base.sqlite")
        answers = answers_of(base)
        stage_ids = {str(r[0]) for r in base.execute("SELECT stage_id FROM rec_stage")} if seen else set()
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
        gate_affil = {}           # 利用者 -> いちばん後の区切りの裏の答え合わせ（affil）の勝ち・負け（履歴がいちばん長い）
        ctally = defaultdict(lambda: [0.0, 0, 0, 0])   # 学習曲線: (利用者, k) -> [勝ち, 組, 入っていた答え, 答え]
        while t.isoformat() < last:
            lo, hi = t.isoformat(), (t + step).isoformat()
            targets = {uid: [r for r in rows if lo < r[0] <= hi] for uid, rows in answers.items()}
            targets = {u: rs for u, rs in targets.items() if len(rs) >= MIN_ANSWERS and any(r[2] for r in rs) and not all(r[2] for r in rs)}
            if targets:
                n_origins += 1
                cut = Path(tmp) / f"cut-{lo}.sqlite"
                split = index_split(seen, lo, stage_ids)
                cut_copy(base, cut, lo, split["later"])
                jobs = [{"uid": u, "variant": v, "ablate": ab, "stages": sorted({r[1] for r in rs})}
                        for u, rs in sorted(targets.items()) for v, ab in variants.items()]
                got = bridge(cut, (t + datetime.timedelta(days=1)).isoformat(), jobs)
                ranks = {(o["uid"], o["variant"]): o["ranks"] for o in got}
                base_runs = [o for o in got if o["variant"] == "base"]
                for o in base_runs:
                    if o.get("gate_affil"):
                        gate_affil[o["uid"]] = o["gate_affil"]
                per_origin.append({"t": lo, "users": len(targets), "answers": sum(len(rs) for rs in targets.values()),
                                   "with_ratings": sum(o.get("n_rated", 0) > 0 for o in base_runs),
                                   "with_recommendations": sum(o["n_ranked"] > 0 for o in base_runs),
                                   "index_dropped": len(split["later"]), "index_changed": split["changed"],
                                   "index_unknown": split["unknown"]})
                if curve:
                    cdb = sqlite3.connect(cut)
                    have = rated_counts(cdb)
                    cdb.close()
                    for k in [*curve, None]:
                        # その区切りで k 件以上の評価がある人だけ（足りない人は全部の評価と同じになる）
                        who = {u: rs for u, rs in targets.items() if k is None or have.get(u, 0) >= k}
                        if not who:
                            continue
                        ck = Path(tmp) / f"curve-{lo}-{k}.sqlite"
                        src = sqlite3.connect(cut)
                        dst = sqlite3.connect(ck)
                        src.backup(dst)
                        src.close()
                        dst.close()
                        if k is not None:
                            keep_oldest(ck, k)
                        got_k = bridge(ck, (t + datetime.timedelta(days=1)).isoformat(),
                                       [{"uid": u, "variant": "base", "ablate": {}, "stages": sorted({r[1] for r in rs})}
                                        for u, rs in sorted(who.items())])
                        ck.unlink()
                        for o in got_k:
                            rs = who[o["uid"]]
                            w, n = pair_wins([(r[2], o["ranks"].get(r[1])) for r in rs])
                            c = ctally[(o["uid"], k)]
                            c[0] += w
                            c[1] += n
                            c[2] += sum(o["ranks"].get(r[1]) is not None for r in rs)
                            c[3] += len(rs)
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
    if curve:
        # 持ち主は除く（ほかの結果と同じ）
        result_curve = curve_summary({key: v for key, v in ctally.items() if key[0] != owner}, [*curve, None])
    result = {"origins": n_origins, "step_days": step_days, "first_answer": first, "last_answer": last,
              "answers_ranked_share": round(coverage[0] / coverage[1], 3) if coverage[1] else None, "per_origin": per_origin}
    if curve:
        result["curve"] = result_curve
    # 裏の答え合わせの affil（測るだけで選ばない）を全員分たす。持ち主は別に出す。区切りが重なるので、1 人 1 回（いちばん後）だけ
    ga = {u: v for u, v in gate_affil.items() if u != owner}
    result["gate_affil"] = {"users": len(ga), "wins": sum(int(v.get("wins", 0)) for v in ga.values()),
                            "losses": sum(int(v.get("losses", 0)) for v in ga.values()),
                            "users_better": sum(v.get("wins", 0) > v.get("losses", 0) for v in ga.values()),
                            "users_worse": sum(v.get("wins", 0) < v.get("losses", 0) for v in ga.values()),
                            **({"owner": gate_affil[owner]} if owner and owner in gate_affil else {})}
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
        # 足して試す部品（H6）: 差は「足した計算 − 今の計算」（正なら足すと当たりが増える）
        tdiffs = {t: [auc_of(u, screen, f"try_{t}") - base_auc[u] for u in others] for t in TRIALS}
        tadj = holm({t: wilcoxon_p(d) for t, d in tdiffs.items()})
        entry["H6"] = {t: {"median_diff": sorted(d)[len(d) // 2] if d else None, "users_better": sum(x > 0 for x in d),
                           "users_worse": sum(x < 0 for x in d),
                           "p_holm": round(tadj[t], 4) if enough else "まだ（人数が足りない）"} for t, d in tdiffs.items()}
        if owner and owner in users:
            entry["owner"] = {"auc": base_auc[owner], **{f"diff_{a}": base_auc[owner] - auc_of(owner, screen, a) for a in ABLATIONS},
                              **{f"gain_{t}": auc_of(owner, screen, f"try_{t}") - base_auc[owner] for t in TRIALS}}
        result[screen] = entry
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("backup", help="復号した控え（backup.sql）")
    ap.add_argument("what", choices=["counts", "logged", "replay", "h3"])
    ap.add_argument("--owner", help="持ち主の user_id（除いて別に出す）")
    ap.add_argument("--min-users", type=int, default=1,
                    help="判定を出す最少の人数（既定 1。§6 の目安は H1 で 15〜20 人、H5 で 30 人）")
    ap.add_argument("--index", type=Path, help="replay: 索引の SQL（build_recommend_index.py --output）")
    ap.add_argument("--extra", type=Path, action="append", default=[],
                    help="replay: ほかに読む SQL（deliver_past.py build の past_stage など。任意）")
    ap.add_argument("--step-days", type=int, default=STEP_DAYS, help="replay: 区切りの長さ（日）")
    ap.add_argument("--curve", action="store_true",
                    help="replay: 学習曲線も出す（評価を古いほうから 1・2・5・10・20 件と全部に絞って測る。#103）")
    ap.add_argument("--seen", type=Path, help="replay: 公演の載った日（取得の作業データの d1/index-hashes.json。#72）")
    a = ap.parse_args(argv)
    if a.what == "replay":
        if not a.index:
            ap.error("replay には --index が要ります")
        seen = json.loads(a.seen.read_text(encoding="utf-8")) if a.seen and a.seen.exists() else None
        out = replay(a.backup, a.index, a.extra, owner=a.owner, min_users=a.min_users, step_days=a.step_days, seen=seen,
                     curve=CURVE if a.curve else None)
        json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
        print()
        return 0
    db = load(a.backup)
    out = (counts(db, a.owner) if a.what == "counts" else h3(db, a.owner, a.min_users) if a.what == "h3"
           else logged(db, a.owner, a.min_users))
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
