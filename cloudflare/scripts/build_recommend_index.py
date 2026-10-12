"""Build the D1 person-score index from the catalogue (step 1 of moving
recommendations off Render).

    python3 cloudflare/scripts/build_recommend_index.py --output /tmp/rec.sql \
        --stats /tmp/rec-stats.json

The Python recommender (`tools/review/user_recommender.py`) re-reads every
catalogue file and re-parses every credit field on each request. Everything that
does not depend on the user is computed here once:

- rec_stage: candidate stages with run dates and parsed credits
- rec_credit: (role, person) -> stages, with role weight and role group
- rec_people: stage -> parsed credits, to build a user's roster from records

The Worker then only reads postings for people the user rated ◎ at least once.
`score_from_index` is the reference for that request-time computation; the
test checks it against `user_recommender.prepare`.

Only public catalogue fields are written. Owner scores, reasons, notes and
reactions (why_b, a, _notes, ...) never enter the index.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "review"))
sys.path.insert(0, str(ROOT / "tools" / "taguri"))

import measure_nets as M                                           # noqa: E402
import recommend2 as RC                                            # noqa: E402
import user_recommender as UR                                      # noqa: E402

PUBLIC_KEYS = ("title", "group", "theater", "pref", "period", "price", "venue", "fields")
MAX_STATEMENT_BYTES = 90_000       # D1 rejects SQL statements over 100 KB


def _period_end(period: str) -> str:
    end = RC.period_end(period)
    return end.isoformat() if end else ""


def _public_entry(entry: dict) -> dict:
    out = {k: entry[k] for k in PUBLIC_KEYS if entry.get(k)}
    url = str(entry.get("url") or "")
    if url.startswith("https://"):
        out["url"] = url
    return out


def build_index(pool: dict[str, dict], fields_by_stage: dict[str, dict], role_group) -> dict:
    """User-independent material. `pool` is `UR.candidate_pool(...)`."""
    stages, postings = {}, []
    for sid, entry in pool.items():
        title = entry.get("title") or ""
        if any(word in title for word in RC.NOT_PLAY_TITLE):
            continue
        period = entry.get("period") or ""
        credits = sorted(set(M.parse_credits(entry.get("fields") or {})))
        stages[sid] = {"title": title, "grp": entry.get("group") or "",
                       "start": RC.period_start(period), "end": _period_end(period),
                       "credits": [list(c) for c in credits],
                       "entry": _public_entry(entry)}
        for role, person in credits:
            postings.append((role, person, sid, RC.ROLE_W.get(role, RC.BACKSTAGE_W),
                             role_group(role)))
    people = {sid: [list(c) for c in sorted(set(M.parse_credits(f)))]
              for sid, f in fields_by_stage.items() if f}
    people = {sid: p for sid, p in people.items() if p}
    return {"stages": stages, "postings": postings, "people": people}


# ---------------------------------------------------------------- request time (reference)

def score_from_index(postings_for, stage_of, rated: list[dict], *, multipliers: dict,
                     today: datetime.date) -> list[dict]:
    """What the Worker computes per request, using only the index.

    `rated`: the user's records with `verdict`, `stage_id`/`key`, `people`
    (from rec_people), `updated_at`, `date`. `postings_for(keys)` returns
    rec_credit rows for (role, person) keys; `stage_of(sid)` returns rec_stage.
    Returns ranked stages with b > 0, ordered as `UR.finish` orders them
    before tour grouping.
    """
    rated = UR.independent_ratings(rated)
    base = sum(r["verdict"] == "◎" for r in rated) / max(len(rated), 1)
    roster = M.build_roster(rated, lambda v: float(v == "◎"))
    # n > 0 and o > 0 are required for a positive part, so only ◎ people are read.
    keys = sorted(k for k, (n, o) in roster.items() if n and o)
    by_stage: dict[str, list] = {}
    for role, person, sid, role_w, group in postings_for(keys):
        n, o = roster[(role, person)]
        contrib = (o + M.SMOOTH_A) / (n + M.SMOOTH_B) - base
        contrib *= n / (n + M.CONF_K) * role_w * multipliers.get(group, 1.0)
        if contrib > 0:
            by_stage.setdefault(sid, []).append([round(contrib, 6), role, person, n, group])
    out, iso = [], today.isoformat()
    for sid, parts in by_stage.items():
        st = stage_of(sid)
        if st is None or (st["end"] and st["end"] < iso):
            continue
        if st["start"] and st["start"] <= iso:
            continue                     # already running: "started", not "ranked"
        parts.sort(key=lambda p: (-p[0], p[1], p[2]))
        b = round(sum(p[0] for p in parts[:M.TOP_N]), 6)
        if b <= 0:
            continue
        strong = sum(multipliers.get(p[4], 1.0) for p in parts if p[1] == "出演" or p[3] >= 2)
        out.append({"stage_id": sid, "b": b, "strong": strong,
                    "parts": [p[:4] for p in parts]})
    out.sort(key=lambda c: (-c["strong"], -c["b"], c["stage_id"]))
    return out


def memory_access(index: dict):
    """Accessors over the in-memory index (same contract as the D1 queries)."""
    by_key: dict = {}
    for row in index["postings"]:
        by_key.setdefault((row[0], row[1]), []).append(row)
    return (lambda keys: [r for k in keys for r in by_key.get(k, [])],
            lambda sid: index["stages"].get(sid))


KEYS_PER_QUERY = 49                # D1 binds at most 100 parameters: ver + 2 per key


def sql_access(con, ver: str, counter: dict | None = None):
    """Accessors over D1/SQLite: the queries the Worker issues.

    `counter["rows"]` accumulates rows read, to estimate the D1 daily quota.
    """
    counter = counter if counter is not None else {}
    counter.setdefault("rows", 0)

    def postings_for(keys):
        out = []
        for i in range(0, len(keys), KEYS_PER_QUERY):
            chunk = keys[i:i + KEYS_PER_QUERY]
            pairs = ",".join("(?,?)" for _ in chunk)
            rows = con.execute(
                "SELECT role,person,stage_id,role_w,role_group FROM rec_credit"
                f" WHERE ver=? AND (role,person) IN (VALUES {pairs})",
                [ver] + [x for k in chunk for x in k]).fetchall()
            counter["rows"] += len(rows)
            out += [tuple(r) for r in rows]
        return out

    def stage_of(sid):
        row = con.execute("SELECT start,end FROM rec_stage WHERE ver=? AND stage_id=?",
                          (ver, sid)).fetchone()
        counter["rows"] += row is not None
        return {"start": row[0], "end": row[1]} if row else None

    return postings_for, stage_of


# ---------------------------------------------------------------- SQL

def version_of(index: dict) -> str:
    blob = json.dumps(index, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


def _q(v) -> str:
    if isinstance(v, (int, float)):
        return repr(float(v))
    return "'" + str(v).replace("'", "''") + "'"


def _inserts(table: str, cols: str, rows: list[tuple]) -> list[str]:
    head = f"INSERT INTO {table}({cols}) VALUES"
    out, cur, size = [], [], len(head)
    for row in rows:
        val = "(" + ",".join(_q(v) for v in row) + ")"
        if cur and size + len(val) + 2 > MAX_STATEMENT_BYTES:
            out.append(head + ",".join(cur) + ";")
            cur, size = [], len(head)
        cur.append(val)
        size += len(val) + 1
    if cur:
        out.append(head + ",".join(cur) + ";")
    return out


def to_sql(index: dict, ver: str) -> list[str]:
    """Insert `ver`, switch to it, then drop other versions (in that order)."""
    dumps = lambda v: json.dumps(v, ensure_ascii=False, sort_keys=True)
    stmts = [f"DELETE FROM {t} WHERE ver={_q(ver)};"
             for t in ("rec_stage", "rec_credit", "rec_people")]
    stmts += _inserts("rec_stage", "ver,stage_id,title,grp,start,end,credits,entry", [
        (ver, sid, s["title"], s["grp"], s["start"], s["end"], dumps(s["credits"]),
         dumps(s["entry"])) for sid, s in sorted(index["stages"].items())])
    stmts += _inserts("rec_credit", "ver,role,person,stage_id,role_w,role_group",
                      [(ver, *r) for r in sorted(set(index["postings"]))])
    stmts += _inserts("rec_people", "ver,stage_id,people",
                      [(ver, sid, dumps(p)) for sid, p in sorted(index["people"].items())])
    stmts.append(f"INSERT INTO rec_meta(k,v) VALUES('current',{_q(ver)}) "
                 "ON CONFLICT(k) DO UPDATE SET v=excluded.v;")
    stmts += [f"DELETE FROM {t} WHERE ver<>{_q(ver)};"
              for t in ("rec_stage", "rec_credit", "rec_people")]
    return stmts


def stats(index: dict, sql_bytes: int) -> dict:
    """Numbers needed to judge the D1 free tier (rows read per request)."""
    per_person: dict = {}
    for role, person, *_ in index["postings"]:
        per_person[(role, person)] = per_person.get((role, person), 0) + 1
    sizes = sorted(per_person.values()) or [0]
    return {"stages": len(index["stages"]), "postings": len(index["postings"]),
            "people": len(per_person), "people_stages": len(index["people"]),
            "postings_per_person": {"median": statistics.median(sizes),
                                    "p90": sizes[int(len(sizes) * 0.9) - 1 if len(sizes) > 1 else 0],
                                    "max": sizes[-1]},
            "sql_bytes": sql_bytes}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--output", required=True, type=Path, help="SQL for wrangler d1 execute --file")
    p.add_argument("--stats", type=Path, help="write size statistics as JSON")
    a = p.parse_args()
    import app as APP
    import digest as DG
    import render_recommend as RR
    try:
        raw, _ = RR.load()
    except FileNotFoundError:
        raw = {}
    pool = UR.candidate_pool(raw, DG.all_candidates())
    if not pool:
        p.error("no candidates under data/; fetch the catalogue first")
    index = build_index(pool, M._fields_by_stage(), APP.group_of)
    stmts = to_sql(index, version_of(index))
    body = "\n".join(stmts) + "\n"
    with os.fdopen(os.open(a.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as out:
        out.write(body)
    st = stats(index, len(body.encode("utf-8")))
    if a.stats:
        a.stats.write_text(json.dumps(st, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(st, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
