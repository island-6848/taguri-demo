#!/usr/bin/env python3
"""Deliver the crawled catalogue (and the synopses read once) to D1.

    python3 cloudflare/scripts/deliver_catalogue.py build --data data --out /tmp/d1 [--index]
    npx wrangler d1 execute taguri-demo --remote --file /tmp/d1/catalogue.sql
    python3 cloudflare/scripts/deliver_catalogue.py commit --data data --out /tmp/d1

The crawler (taguri-crawler, GitHub Actions) runs this after each crawl. It
writes **only rows that changed** since the last delivery: D1's free tier
allows 100,000 rows written per day, and the catalogue holds thousands of
stages that rarely change. What was delivered is kept in
`data/d1/delivered.json` (row hashes and the index version), which the crawler
carries between runs on its `state` branch. `commit` updates it only after
wrangler succeeded, so a failed upload is retried in full the next day.

- catalogue: upsert only, never delete (a record linked to an ended stage keeps
  its name). Public fields only (`convert_catalogue.public_candidate`); the
  synopsis and its content words come from `data/credits/themes.jsonl`, read
  once per stage by the owner's Claude (docs/knowledge dec-synopsis-reader-claude).
- rec_meta: `catalogue_scan` / `catalogue_delivered` / `catalogue_upcoming`, for
  the public `/api/health` (dates and counts only).
- `--index`: the person-score index (`build_recommend_index.py`) and the stage
  names the original screens show (`build_stage_labels.py`, migration 0011),
  each uploaded only when its version changed and the day's write budget allows it.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from convert_catalogue import public_candidate                     # noqa: E402
import free_tier as FT                                             # noqa: E402

JST = datetime.timezone(datetime.timedelta(hours=9))
WRITE_BUDGET = 60_000          # of the 100,000 rows/day free tier; the rest is for users
ROWS_PER_UPSERT = 2            # the row and the catalogue_date index entry
STATE = Path("d1") / "delivered.json"


def _jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").split("\n") if l.strip()]


def themes_by_stage(data: Path) -> dict[str, dict]:
    """Candidate-side synopses that passed the verbatim check (empty ones are skipped)."""
    out = {}
    for r in _jsonl(data / "credits" / "themes.jsonl"):
        if r.get("side") == "candidate" and r.get("synopsis"):
            out[str(r["id"])] = r
    return out


def catalogue_rows(data: Path, today: datetime.date) -> dict[str, list[str]]:
    """{stage_id: row} for stages that have not ended. Unreadable rows are skipped, not invented."""
    themes = themes_by_stage(data)
    rows: dict[str, list[str]] = {}
    for c in _jsonl(data / "review" / "candidates.jsonl"):
        if c.get("ended"):
            continue
        sid = str(c.get("stage_id") or "")
        fields = c.get("fields") if isinstance(c.get("fields"), dict) else {}
        value = {"stage_id": sid, "title": c.get("title"), "period": c.get("period"),
                 "venue": c.get("venue") or c.get("theater") or "", "group": c.get("group"),
                 "fields": fields, "url": _official_url(fields)}
        t = themes.get(sid)
        if t:
            value["synopsis"] = t["synopsis"]
            value["words"] = [e["word"] for e in t.get("elements") or [] if isinstance(e, dict) and e.get("word")]
        try:
            row = public_candidate(value)
        except ValueError:
            continue
        if json.loads(row[5])["end_date"] < today.isoformat():
            continue
        rows[sid] = row
    return rows


def _official_url(fields: dict) -> str:
    m = re.search(r"https://[^\s\"'<>]+", str(fields.get("公式／劇場サイト") or ""))
    return m.group(0) if m else ""


def _q(v: str) -> str:
    return "'" + str(v).replace("'", "''") + "'"


def _hash(row: list[str]) -> str:
    return hashlib.sha256(json.dumps(row, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


def upsert_sql(row: list[str]) -> str:
    return ("INSERT INTO catalogue(id,title,date,venue,url,metadata) VALUES("
            + ",".join(map(_q, row)) + ") ON CONFLICT(id) DO UPDATE SET title=excluded.title,"
            "date=excluded.date,venue=excluded.venue,url=excluded.url,metadata=excluded.metadata;")


def meta_sql(k: str, v: str) -> str:
    return f"INSERT INTO rec_meta(k,v) VALUES({_q(k)},{_q(v)}) ON CONFLICT(k) DO UPDATE SET v=excluded.v;"


def scan_date(data: Path) -> str:
    try:
        d = json.loads((data / "review" / "candidates_scan.json").read_text(encoding="utf-8")).get("date")
        return str(d)[:10] if d else ""
    except (OSError, json.JSONDecodeError, AttributeError):
        return ""


def build_index(out: Path) -> tuple[str, int, Path] | None:
    """Run build_recommend_index.py; (version, rows written, sql). None if it cannot run here."""
    sql, st = out / "index.sql", out / "index-stats.json"
    for f in (sql, st):
        f.unlink(missing_ok=True)
    r = subprocess.run([sys.executable, str(HERE / "build_recommend_index.py"),
                        "--output", str(sql), "--stats", str(st)], cwd=ROOT)
    if r.returncode != 0 or not sql.exists():
        return None
    m = re.search(r"VALUES\('current','([0-9a-f]+)'\)", sql.read_text(encoding="utf-8"))
    if not m:
        return None
    # The upload writes every row once and deleting the old version writes them again.
    return m.group(1), 2 * json.loads(st.read_text(encoding="utf-8"))["rows_written"], sql


def build_labels(out: Path) -> tuple[str, int, Path] | None:
    """Run build_stage_labels.py; (version, rows written, sql). None if it cannot run here."""
    sql = out / "labels.sql"
    sql.unlink(missing_ok=True)
    r = subprocess.run([sys.executable, str(HERE / "build_stage_labels.py"), "--output", str(sql)],
                       cwd=ROOT, capture_output=True, text=True)
    print(r.stderr, end="", file=sys.stderr)
    if r.returncode != 0 or not sql.exists():
        return None
    m = re.search(r"VALUES\('stage_label','([0-9a-f]+)'\)", sql.read_text(encoding="utf-8"))
    if not m:
        return None
    # Inserting a version and deleting the previous one write each row twice.
    return m.group(1), 2 * json.loads(r.stdout.strip().splitlines()[-1])["stages"], sql


def build_cards(out: Path, today: datetime.date) -> tuple[str, int, Path] | None:
    """Run build_cards.py; (version, rows written, sql). None if it cannot run here."""
    sql = out / "cards.sql"
    sql.unlink(missing_ok=True)
    r = subprocess.run([sys.executable, str(HERE / "build_cards.py"), "--output", str(sql),
                        "--today", today.isoformat()], cwd=ROOT, capture_output=True, text=True)
    print(r.stderr, end="", file=sys.stderr)
    if r.returncode != 0 or not sql.exists():
        return None
    m = re.search(r"VALUES\('rec_card','([0-9a-f]+)'\)", sql.read_text(encoding="utf-8"))
    if not m:
        return None
    # Inserting a version and deleting the previous one write each row twice.
    return m.group(1), 2 * json.loads(r.stdout.strip().splitlines()[-1])["stages"], sql


def build(data: Path, out: Path, today: datetime.date, with_index: bool, budget: int) -> dict:
    prev = json.loads((data / STATE).read_text(encoding="utf-8")) if (data / STATE).exists() else {}
    seen: dict[str, str] = dict(prev.get("rows") or {})
    rows = catalogue_rows(data, today)
    changed = {sid: row for sid, row in rows.items() if seen.get(sid) != _hash(row)}
    stmts = [upsert_sql(row) for _, row in sorted(changed.items())]
    for sid, row in changed.items():
        seen[sid] = _hash(row)
    writes = ROWS_PER_UPSERT * len(stmts)
    if writes > budget:
        raise SystemExit(f"{len(stmts)} catalogue rows exceed today's write budget ({writes} > {budget}); "
                         "raise --budget only after checking the D1 usage")
    meta = {"catalogue_scan": scan_date(data),
            "catalogue_delivered": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "catalogue_upcoming": str(len(rows))}
    stmts += [meta_sql(k, v) for k, v in meta.items() if v]
    writes += len(meta)
    report = {"stages": len(rows), "changed": len(changed), "writes": writes,
              "with_synopsis": sum(1 for r in rows.values() if json.loads(r[5]).get("synopsis"))}
    state = {"rows": seen, "index": prev.get("index", ""), "labels": prev.get("labels", ""),
             "cards": prev.get("cards", "")}
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    if with_index:
        got = build_index(out)
        if got is None:
            report["index"] = "not built (see the log above)"
        elif got[0] == prev.get("index"):
            report["index"] = "unchanged"
        elif writes + got[1] > budget:
            report["index"] = f"skipped: {got[1]} writes would exceed the budget"
        else:
            shutil.move(got[2], out / "index-upload.sql")
            state["index"] = got[0]
            report["index"] = f"version {got[0]} ({got[1]} writes)"
            writes += got[1]
            report["writes"] = writes
        got = build_labels(out)
        if got is None:
            report["labels"] = "not built (see the log above)"
        elif got[0] == prev.get("labels"):
            report["labels"] = "unchanged"
        elif writes + got[1] > budget:
            report["labels"] = f"skipped: {got[1]} writes would exceed the budget"
        else:
            shutil.move(got[2], out / "labels-upload.sql")
            state["labels"] = got[0]
            report["labels"] = f"version {got[0]} ({got[1]} writes)"
            writes += got[1]
            report["writes"] = writes
        # The recommend screen's cards (build_cards.py). Their dates are as of today, so a
        # new version comes most days: about twice the number of coming stages in writes.
        got = build_cards(out, today)
        if got is None:
            report["cards"] = "not built (see the log above)"
        elif got[0] == prev.get("cards"):
            report["cards"] = "unchanged"
        elif writes + got[1] > budget:
            report["cards"] = f"skipped: {got[1]} writes would exceed the budget"
        else:
            shutil.move(got[2], out / "cards-upload.sql")
            state["cards"] = got[0]
            report["cards"] = f"version {got[0]} ({got[1]} writes)"
            writes += got[1]
            report["writes"] = writes
    (out / "catalogue.sql").write_text("\n".join(stmts) + "\n", encoding="utf-8")
    (out / "pending.json").write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    return report


def commit(data: Path, out: Path) -> None:
    (data / STATE).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(out / "pending.json", data / STATE)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["build", "commit"])
    ap.add_argument("--data", type=Path, default=ROOT / "data")
    ap.add_argument("--out", type=Path, required=True, help="directory for the SQL files (replaced)")
    ap.add_argument("--index", action="store_true", help="also upload the person-score index if it changed")
    ap.add_argument("--budget", type=int, default=WRITE_BUDGET)
    ap.add_argument("--today", default=datetime.datetime.now(JST).date().isoformat())
    a = ap.parse_args()
    # The index / labels / cards builders run with cwd=ROOT, so a relative --out (the workflow passes
    # ../d1-out from cloudflare/) pointed elsewhere and they failed with FileNotFoundError: the index
    # was never delivered and the service had no recommendations (q-interest-no-reco-prod).
    a.data, a.out = a.data.resolve(), a.out.resolve()
    if a.action == "commit":
        commit(a.data, a.out)
        print("delivered state saved")
        return 0
    # 今日（UTC）の D1 の書き込みの残り（free_tier.py の控え）を越えない。書く前に控えに足す
    budget = min(a.budget, FT.d1_left(a.data))
    report = build(a.data, a.out, datetime.date.fromisoformat(a.today), a.index, budget)
    FT.d1_spend(a.data, report["writes"])
    report["d1_left_today"] = FT.d1_left(a.data)
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
