#!/usr/bin/env python3
"""Upload the past stages read by tools/review/fetch_past_stages.py into D1 (past_stage).

    python3 cloudflare/scripts/deliver_past.py build --data data --out d1-past
    npx wrangler d1 execute taguri-demo --remote --file d1-past/past-upload.sql
    python3 cloudflare/scripts/deliver_past.py commit --data data --out d1-past

Only the lines of data/past/stages.jsonl added since the last upload are sent
(the count is kept in data/d1/past_delivered.json and saved only by `commit`,
after wrangler succeeded). Each row costs two writes (the row and its tkey
index entry); `--budget` caps a day's upload so the catalogue job and users
keep the rest of the free tier. Rows left over go the next day.

The Worker uses these rows only to link a user's record to the stage they saw
(docs/knowledge: q-auto-link-past). `people` is measure_nets.parse_credits of
the page's credits, the same form as rec_people.people.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tools" / "review"))
sys.path.insert(0, str(HERE))

import measure_nets as M                                           # noqa: E402
from build_recommend_index import _inserts                         # noqa: E402

STATE = Path("d1") / "past_delivered.json"
ROWS = Path("past") / "stages.jsonl"
WRITES_PER_ROW = 2
BUDGET = 20_000


def people_of(fields: dict) -> list:
    return [list(c) for c in sorted(set(M.parse_credits(fields or {})))]


def row_values(r: dict) -> tuple:
    return (str(r["stage_id"]), r.get("title") or "", M.R.title_key(r.get("title") or ""),
            r.get("start") or "", r.get("end") or "", r.get("theater") or "",
            r.get("group") or "", r.get("pref") or "",
            json.dumps(people_of(r.get("fields") or {}), ensure_ascii=False, sort_keys=True))


def build(data: Path, out: Path, budget: int) -> dict:
    prev = json.loads((data / STATE).read_text(encoding="utf-8")) if (data / STATE).exists() else {}
    done = int(prev.get("lines") or 0)
    lines = (data / ROWS).read_text(encoding="utf-8").splitlines() if (data / ROWS).exists() else []
    take = max(0, budget // WRITES_PER_ROW)
    new = lines[done:done + take]
    rows = []
    for line in new:
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("stage_id") and r.get("title"):
            rows.append(row_values(r))
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    stmts = [s.replace("INSERT INTO", "INSERT OR REPLACE INTO", 1) for s in
             _inserts("past_stage", "stage_id,title,tkey,start,end,venue,grp,pref,people", rows)]
    if stmts:
        (out / "past-upload.sql").write_text("\n".join(stmts) + "\n", encoding="utf-8")
    (out / "pending.json").write_text(json.dumps({"lines": done + len(new)}), encoding="utf-8")
    return {"rows": len(rows), "writes": WRITES_PER_ROW * len(rows),
            "delivered_before": done, "left": max(0, len(lines) - done - len(new))}


def commit(data: Path, out: Path) -> None:
    (data / STATE).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(out / "pending.json", data / STATE)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["build", "commit"])
    ap.add_argument("--data", type=Path, default=ROOT / "data")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--budget", type=int, default=BUDGET)
    a = ap.parse_args()
    if a.action == "commit":
        commit(a.data, a.out)
        print("past stages: delivered state saved")
        return 0
    print(json.dumps(build(a.data, a.out, a.budget), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
