#!/usr/bin/env python3
"""Upload the past stages read by tools/review/fetch_past_stages.py into D1 (past_stage).

    python3 cloudflare/scripts/deliver_past.py build --data data --out d1-past
    npx wrangler d1 execute taguri-demo --remote --file d1-past/past-upload.sql
    python3 cloudflare/scripts/deliver_past.py commit --data data --out d1-past

Only the lines of data/past/stages.jsonl added since the last upload are sent
(the count is kept in data/d1/past_delivered.json and saved only by `commit`,
after wrangler succeeded). Each row costs three writes (the row, its primary-key index and its tkey
index entry); `--budget` caps a day's upload so the catalogue job and users
keep the rest of the free tier. Rows left over go the next day.

The Worker uses these rows to link a user's record to the stage they saw
(docs/knowledge: q-auto-link-past) and, for a rated record, as the material the
recommendations learn from. `people` is measure_nets.parse_credits of the page's
credits plus the kind-of-show tags (user_recommender.stage_tags: form, source,
translation, genre), the same form as rec_people.people (build_recommend_index).
Past pages carry no synopsis, so there are no #題材 tags.

When the form of `people` changes, PEOPLE_REV goes up and every line is sent
again (INSERT OR REPLACE), within the same daily budget.
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
import user_recommender as UR                                      # noqa: E402
from build_recommend_index import _inserts                         # noqa: E402
import free_tier as FT                                             # noqa: E402

STATE = Path("d1") / "past_delivered.json"
ROWS = Path("past") / "stages.jsonl"
WRITES_PER_ROW = 3             # the row, its primary-key index and past_stage_tkey (measured: 30,000 rows_written for 10,001 rows)
# 送り直しの UPDATE は people の列だけ（索引の無い列）なので 1 行 1 書き込みのはず。測るまでは 2 と見て抑える
WRITES_PER_UPDATE = 2
BUDGET = 20_000
# 2: 種類の言葉（#形式・#原作など）も入れる。起案者の指摘（2026-10-18）「30 件くらい過去の記録を足したのに、
# 全然おすすめに反映されてる感じがしない」。過去の公演は名前だけだったので、形式・原作・ジャンルの好みも
# 感想の好み（#104）も、過去の記録からは学べなかった
PEOPLE_REV = 2


def people_of(fields: dict) -> list:
    return [list(c) for c in sorted(set(M.parse_credits(fields or {})))]


def people_and_tags(r: dict) -> list:
    """build_recommend_index.build_index の rec_people と同じ: クレジットと種類の言葉（stage_tags）。"""
    fields = r.get("fields") or {}
    credits = sorted(set(M.parse_credits(fields)))
    tags = UR.stage_tags(r.get("title") or "", [fields.get("劇場", "")], credits,
                         source=UR.source_text(fields), group=r.get("group") or "")
    return [list(c) for c in sorted(set(credits) | set(tags))]


def row_values(r: dict) -> tuple:
    return (str(r["stage_id"]), r.get("title") or "", M.R.title_key(r.get("title") or ""),
            r.get("start") or "", r.get("end") or "", r.get("theater") or "",
            r.get("group") or "", r.get("pref") or "",
            json.dumps(people_and_tags(r), ensure_ascii=False, sort_keys=True))


def _people_updates(rows: list[tuple[str, str]]) -> list[str]:
    """送り直し: people の列だけを書き換える（索引の付いた列は変えないので、1 行の書き込みで済む）。"""
    tail = ") UPDATE past_stage SET people=(SELECT p FROM v WHERE v.id=past_stage.stage_id) WHERE stage_id IN (SELECT id FROM v);"
    stmts = _inserts("v", "id,p", rows)
    return ["WITH v(id,p) AS (VALUES" + x[len("INSERT INTO v(id,p) VALUES"):-1] + tail for x in stmts]


def build(data: Path, out: Path, budget: int) -> dict:
    prev = json.loads((data / STATE).read_text(encoding="utf-8")) if (data / STATE).exists() else {}
    done = int(prev.get("lines") or 0)
    # 形が変わったら（PEOPLE_REV）、送り済みの行の people を UPDATE で送り直す（refresh_to まで）。
    # INSERT OR REPLACE で送り直すと、消す分と入れる分（主キーと tkey の索引も）を数えられて倍かかる
    if int(prev.get("rev") or 1) == PEOPLE_REV:
        refreshed, refresh_to = int(prev.get("refreshed") or 0), int(prev.get("refresh_to") or 0)
    else:
        refreshed, refresh_to = 0, done
    # 改行は "\n" だけで区切る（splitlines は題名の中の U+2028 などでも切ってしまう）
    text = (data / ROWS).read_text(encoding="utf-8") if (data / ROWS).exists() else ""
    lines = [line for line in text.split("\n") if line.strip()]
    redo = lines[refreshed:min(refresh_to, refreshed + max(0, budget // WRITES_PER_UPDATE))]
    updates = []
    for line in redo:
        r = json.loads(line)
        if r.get("stage_id") and r.get("title"):
            updates.append((str(r["stage_id"]), row_values(r)[-1]))
    budget -= WRITES_PER_UPDATE * len(updates)
    take = max(0, budget // WRITES_PER_ROW)
    new = lines[done:done + take]
    rows = []
    for line in new:
        r = json.loads(line)
        if r.get("stage_id") and r.get("title"):
            rows.append(row_values(r))
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    stmts = _people_updates(updates) + [s.replace("INSERT INTO", "INSERT OR REPLACE INTO", 1) for s in
                                        _inserts("past_stage", "stage_id,title,tkey,start,end,venue,grp,pref,people", rows)]
    if stmts:
        (out / "past-upload.sql").write_text("\n".join(stmts) + "\n", encoding="utf-8")
    (out / "pending.json").write_text(json.dumps({"lines": done + len(new), "rev": PEOPLE_REV,
                                                  "refreshed": refreshed + len(redo), "refresh_to": refresh_to}), encoding="utf-8")
    return {"rows": len(rows), "updated": len(updates), "writes": WRITES_PER_ROW * len(rows) + WRITES_PER_UPDATE * len(updates),
            "delivered_before": done, "left": max(0, len(lines) - done - len(new)),
            "to_refresh": max(0, refresh_to - refreshed - len(redo))}


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
    # 今日（UTC）の D1 の書き込みの残り（free_tier.py の控え）を越えない。書く前に控えに足す
    report = build(a.data, a.out, min(a.budget, FT.d1_left(a.data)))
    FT.d1_spend(a.data, report["writes"])
    report["d1_left_today"] = FT.d1_left(a.data)
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
