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
- venue_census + rec_meta `venue_counts` (migration 0027): the denominator of the theatre-conquest map,
  every venue named by two or more crawled stages (coming and past), halls kept apart. Only changed rows,
  and only on a day with room for all of them.
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
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from convert_catalogue import public_candidate                     # noqa: E402
import free_tier as FT                                             # noqa: E402
sys.path.insert(0, str(HERE.parents[1] / "tools" / "review"))
import user_recommender as UR                                      # noqa: E402

JST = datetime.timezone(datetime.timedelta(hours=9))
WRITE_BUDGET = 60_000          # of the 100,000 rows/day free tier; the rest is for users
# D1 counts index writes in rows_written (d1-meta-size-after). Every table here has a TEXT or composite
# primary key, so SQLite keeps it in its own index: one row costs the row, the key index and any other
# index (measured 2026-10-15: past_stage 30,000 rows_written for 10,001 rows; d1-writes-undercounted).
ROWS_PER_UPSERT = 3            # the row, its primary-key index and the catalogue_date index
VENUE_WRITES = 2               # venue_pref: the row and its primary-key index
META_WRITES = 2                # rec_meta: the row and its primary-key index
CENSUS_WRITES = 2              # venue_census (migration 0027): the row and its primary-key index
INDEX_WRITES_PER_ROW = 2       # rec_* / stage_label / rec_card rows: the row and its primary-key index
# rec_stage の行はさらに開始日（0019）と tour（0038）の索引で 2、rec_card の行は tour の索引（0038）で 1 多い
STAGE_EXTRA_WRITES = 2
CARD_WRITES_PER_ROW = INDEX_WRITES_PER_ROW + 1
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
            # 公演の形式の言葉は、読み取りが「題材」と書いたときだけ（build_recommend_index.theme_terms と同じ）
            value["words"] = [e["word"] for e in t.get("elements") or [] if isinstance(e, dict) and e.get("word")
                              and (e.get("kind") == "題材" or UR.M.norm(e["word"]) not in UR.FORM_WORDS)]
        try:
            row = public_candidate(value)
        except ValueError:
            continue
        if json.loads(row[5])["end_date"] < today.isoformat():
            continue
        rows[sid] = row
    return rows


def venue_prefs(data: Path) -> dict[str, str]:
    """{venue: prefecture} from the crawled candidates, for venues whose prefecture is one and the same
    in every candidate that names it (the catalogue rows carry no prefecture; migration 0024)."""
    seen: dict[str, set[str]] = {}
    for c in _jsonl(data / "review" / "candidates.jsonl"):
        venue = str(c.get("venue") or c.get("theater") or "").strip()
        pref = str(c.get("pref") or "").strip()
        if venue and pref:
            seen.setdefault(venue, set()).add(pref)
    return {v: next(iter(ps)) for v, ps in sorted(seen.items()) if len(ps) == 1}


def venue_sql(venue: str, pref: str) -> str:
    return (f"INSERT INTO venue_pref(venue,pref) VALUES({_q(venue)},{_q(pref)}) "
            "ON CONFLICT(venue) DO UPDATE SET pref=excluded.pref;")


# 劇場制覇マップの分母（migration 0027、mock-theater-conquest）。同じ建物のホールはまとめない
PREFS = ("北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県", "茨城県", "栃木県", "群馬県",
         "埼玉県", "千葉県", "東京都", "神奈川県", "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県",
         "岐阜県", "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県", "奈良県", "和歌山県",
         "鳥取県", "島根県", "岡山県", "広島県", "山口県", "徳島県", "香川県", "愛媛県", "高知県", "福岡県",
         "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県")
# 会場でないもの（配信・場所を伏せた回・道順・複数の会場を並べた書き方）
NOT_A_VENUE = re.compile(r"配信|某所|徒歩|オンライン|未定|ほか|他会場|[、/／,]|にて|特設|会場|各地|ウェディング|ホテル")
CENSUS_MIN_SHOWS = 2


def venue_key(name: str) -> str:
    """The venue name as the map matches it (screens/conquest.js venueKey): NFKC, no whitespace."""
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(name or "")))


def venue_census(data: Path) -> dict[str, str]:
    """{venue: prefecture} of the venues named by at least CENSUS_MIN_SHOWS crawled stages (coming and
    past, each stage once). A venue named under two prefectures takes the one most of its stages give."""
    shows: dict[str, dict[str, int]] = {}
    done: set[str] = set()
    for rel in (Path("review") / "candidates.jsonl", Path("past") / "stages.jsonl"):
        for c in _jsonl(data / rel):
            sid = str(c.get("stage_id") or "")
            if not sid or sid in done:
                continue
            done.add(sid)
            v = venue_key(c.get("venue") or c.get("theater") or "")
            p = str(c.get("pref") or "").strip()
            if not v or len(v) > 30 or NOT_A_VENUE.search(v) or p not in PREFS:
                continue
            by = shows.setdefault(v, {})
            by[p] = by.get(p, 0) + 1
    return {v: min(by, key=lambda p: (-by[p], PREFS.index(p))) for v, by in sorted(shows.items())
            if sum(by.values()) >= CENSUS_MIN_SHOWS}


def census_counts(census: dict[str, str]) -> str:
    """rec_meta 'venue_counts': {prefecture: venues} in the order of PREFS."""
    n = {p: 0 for p in PREFS}
    for p in census.values():
        n[p] += 1
    return json.dumps({p: k for p, k in n.items() if k}, ensure_ascii=False, separators=(",", ":"))


def census_sql(venue: str, pref: str | None) -> str:
    if pref is None:
        return f"DELETE FROM venue_census WHERE venue={_q(venue)};"
    return (f"INSERT INTO venue_census(venue,pref) VALUES({_q(venue)},{_q(pref)}) "
            "ON CONFLICT(venue) DO UPDATE SET pref=excluded.pref;")


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


INDEX_HASHES = Path("d1") / "index-hashes.json"


# 索引を入れるときも、題名（stage_label）とカード（rec_card）の毎日の入れ替えの分は残す
# （Catalog #6 で約 9,600 と 3,100）。索引の初回は全部で約 5 万行なので、何日かに分けて入れる（q-index-first-load）。
# 0038 で rec_card に tour の索引を足したので、カードの分を 1 行 1 つ（入れる・消すで約 3,100）多く残す。
LABELS_CARDS_RESERVE = 18_000
# 1 回の wrangler d1 execute に送る大きさ。2026-10-16 の索引 2 万行を 1 つのファイルで送ったら、D1 の
# import が 60 秒で "Upstream service unavailable [code: 7009]" になった（Catalog #7、q-index-load-now）。
# 文の切れ目で分け、1 つずつ送る。どの文も upsert か delete なので、途中で止まっても送り直してよい
UPLOAD_PART_BYTES = 1_000_000


def split_upload(sql: Path, stem: str, max_bytes: int = UPLOAD_PART_BYTES) -> list[Path]:
    """Split one SQL file (one statement per line) into stem-01.sql, stem-02.sql, … of at most max_bytes.
    The order is kept, so the rec_meta line at the end stays in the last part."""
    parts: list[list[str]] = [[]]
    size = 0
    for line in sql.read_text(encoding="utf-8").splitlines(keepends=True):
        n = len(line.encode("utf-8"))
        if parts[-1] and size + n > max_bytes:
            parts.append([])
            size = 0
        parts[-1].append(line)
        size += n
    out = []
    for i, lines in enumerate(p for p in parts if p):
        f = sql.parent / f"{stem}-{i + 1:02d}.sql"
        f.write_text("".join(lines), encoding="utf-8")
        out.append(f)
    sql.unlink()
    return out


def build_index(out: Path, data: Path, max_rows: int | None = None) -> tuple[str, int, Path, int, int] | None:
    """Run build_recommend_index.py in diff mode; (revision, writes, sql, rows changed). None if it cannot run here.

    Only rows that changed since the last delivery are upserted and rows that are gone are deleted
    (q-index-incremental); the hashes of what was sent wait in out/ until commit()."""
    sql, st, hashes = out / "index.sql", out / "index-stats.json", out / "index-hashes.json"
    for f in (sql, st, hashes):
        f.unlink(missing_ok=True)
    args = [sys.executable, str(HERE / "build_recommend_index.py"), "--output", str(sql), "--stats", str(st),
            "--hashes-out", str(hashes)]
    if (data / INDEX_HASHES).exists():
        args += ["--prev-hashes", str(data / INDEX_HASHES)]
    if max_rows is not None:
        args += ["--max-rows", str(max(0, max_rows))]
    r = subprocess.run(args, cwd=ROOT)
    if r.returncode != 0 or not sql.exists():
        return None
    d = json.loads(st.read_text(encoding="utf-8")).get("diff") or {}
    if not d.get("rev"):
        return None
    n = int(d.get("upserted", 0)) + int(d.get("deleted", 0))
    # Each row changed or deleted costs the row and its key index; a rec_stage row also its start and tour indexes.
    return (d["rev"], INDEX_WRITES_PER_ROW * n + STAGE_EXTRA_WRITES * int(d.get("stages_upserted", 0)), sql, n,
            int(d.get("left", 0)))


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
    # Each row is written with its key index; deleting the previous version writes them again (ops in build).
    return m.group(1), INDEX_WRITES_PER_ROW * json.loads(r.stdout.strip().splitlines()[-1])["stages"], sql


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
    # Each row is written with its key and tour indexes; deleting the previous version writes them again (ops in build).
    return m.group(1), CARD_WRITES_PER_ROW * json.loads(r.stdout.strip().splitlines()[-1])["stages"], sql


def build(data: Path, out: Path, today: datetime.date, with_index: bool, budget: int,
          index_only: bool = False) -> dict:
    """`index_only`: the manual index-only run of the crawler (q-index-load-now). The catalogue rows,
    venues, labels and cards are left for the daily run, so the whole of today's budget goes to the index."""
    prev = json.loads((data / STATE).read_text(encoding="utf-8")) if (data / STATE).exists() else {}
    seen: dict[str, str] = dict(prev.get("rows") or {})
    rows = {} if index_only else catalogue_rows(data, today)
    changed = {sid: row for sid, row in rows.items() if seen.get(sid) != _hash(row)}
    stmts = [upsert_sql(row) for _, row in sorted(changed.items())]
    for sid, row in changed.items():
        seen[sid] = _hash(row)
    # 劇場の都道府県: 変わった行だけ（1 行 1 書き込み）。一覧の行を書き直さずに都道府県を付ける
    venues = {} if index_only else venue_prefs(data)
    prev_venues: dict[str, str] = dict(prev.get("venues") or {})
    venue_changed = {v: p for v, p in venues.items() if prev_venues.get(v) != p}
    stmts += [venue_sql(v, p) for v, p in venue_changed.items()]
    writes = ROWS_PER_UPSERT * len(changed) + VENUE_WRITES * len(venue_changed)
    if writes > budget:
        raise SystemExit(f"{len(stmts)} catalogue rows exceed today's write budget ({writes} > {budget}); "
                         "raise --budget only after checking the D1 usage")
    # 劇場制覇マップの分母: 変わった行だけ。今日の残りに収まらなければ、まるごと次の日に回す
    prev_census: dict[str, str] = dict(prev.get("census") or {})
    census = prev_census if index_only else venue_census(data)
    census_changed = {v: p for v, p in census.items() if prev_census.get(v) != p}
    census_changed.update({v: None for v in prev_census if v not in census})
    counts = census_counts(census)
    census_writes = CENSUS_WRITES * len(census_changed) + (META_WRITES if counts != prev.get("census_counts") else 0)
    if census_writes and writes + census_writes + META_WRITES * 3 > budget:
        census_report = f"skipped: {census_writes} writes would exceed the budget"
        census, counts = prev_census, prev.get("census_counts", "")
    else:
        census_report = f"{len(census)} venues ({len(census_changed)} changed)"
        stmts += [census_sql(v, p) for v, p in sorted(census_changed.items())]
        if counts != prev.get("census_counts"):
            stmts.append(meta_sql("venue_counts", counts))
        writes += census_writes
    meta = {"catalogue_scan": scan_date(data),
            "catalogue_delivered": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "catalogue_upcoming": str(len(rows))}
    if index_only:
        meta = {}
    stmts += [meta_sql(k, v) for k, v in meta.items() if v]
    writes += META_WRITES * len(meta)
    report = {"stages": len(rows), "changed": len(changed), "venues_changed": len(venue_changed), "writes": writes,
              "with_synopsis": sum(1 for r in rows.values() if json.loads(r[5]).get("synopsis")),
              "venue_census": census_report}
    state = {"rows": seen, "venues": {**prev_venues, **venues}, "index": prev.get("index", ""), "labels": prev.get("labels", ""),
             "cards": prev.get("cards", ""), "census": census, "census_counts": counts}
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    if with_index or index_only:
        reserve = 0 if index_only else LABELS_CARDS_RESERVE
        # 1 行は行＋主キーの索引で 2、rec_stage はさらに 2。多めに 3 で割って、今日入れられる行数にする
        # （公演ごとに rec_stage 1 行と rec_people・rec_credit の行をまとめて選ぶので、平均は 3 を越えない。
        # 越えた日は下の「writes would exceed the budget」で送らない）
        got = build_index(out, data, (budget - writes - reserve) // (INDEX_WRITES_PER_ROW + 1))
        if got is None:
            report["index"] = "not built (see the log above)"
        elif got[3] == 0 and got[4]:
            report["index"] = f"skipped: no room in today's budget ({got[4]} rows left)"
            (out / "index-hashes.json").unlink(missing_ok=True)
        elif got[0] == prev.get("index") or got[3] == 0:
            report["index"] = "unchanged"
            (out / "index-hashes.json").unlink(missing_ok=True)
        elif writes + got[1] > budget:
            report["index"] = f"skipped: {got[1]} writes would exceed the budget"
            (out / "index-hashes.json").unlink(missing_ok=True)       # not sent: keep the old hashes
        else:
            report["index_parts"] = len(split_upload(got[2], "index-upload"))
            # 全部入れ終えたときだけ版を控える（途中なら、次回も同じ版の残りを送る）
            if not got[4]:
                state["index"] = got[0]
            report["index"] = (f"revision {got[0]} ({got[3]} rows changed, {got[1]} writes"
                               + (f", {got[4]} rows left for the next delivery)" if got[4] else ")"))
            writes += got[1]
            report["writes"] = writes
    if with_index and not index_only:
        got = build_labels(out)
        got = got and (got[0], got[1] * (2 if prev.get("labels") else 1), got[2])   # + deleting the previous version
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
        got = got and (got[0], got[1] * (2 if prev.get("cards") else 1), got[2])   # + deleting the previous version
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
    # 索引だけの実行では空（wrangler には送らない）
    (out / "catalogue.sql").write_text("\n".join(stmts) + "\n" if stmts else "", encoding="utf-8")
    (out / "pending.json").write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    return report


def sent_files(out: Path) -> list[Path]:
    """The SQL files the workflow sends with wrangler (an empty catalogue.sql is not sent)."""
    files = [out / "catalogue.sql"] if (out / "catalogue.sql").exists() and (out / "catalogue.sql").stat().st_size else []
    files += sorted(out.glob("index-upload-*.sql"))
    return files + [out / f for f in ("labels-upload.sql", "cards-upload.sql") if (out / f).exists()]


def settle(data: Path, out: Path) -> str:
    """Replace today's estimate with what D1 counted (rows_written in each file's wrangler log, <file>.log).
    Only when every sent file has its number; otherwise the estimate stays (it is never less)."""
    spent = out / "spent.json"
    if not spent.exists():
        return "no estimate to settle"
    s = json.loads(spent.read_text(encoding="utf-8"))
    measured = []
    for f in sent_files(out):
        log = f.with_name(f.name + ".log")
        n = FT.rows_written(log.read_text(encoding="utf-8", errors="replace")) if log.exists() else None
        if n is None:
            return f"kept the estimate {s['writes']} (no rows_written for {f.name})"
        measured.append(n)
    total = sum(measured)
    day = FT.d1_settle(data, s["day"], s["writes"], total)
    spent.unlink()
    return f"settled {s['day']}: estimate {s['writes']} -> D1 counted {total} (day total {day})"


def commit(data: Path, out: Path) -> None:
    print(settle(data, out))
    (data / STATE).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(out / "pending.json", data / STATE)
    # The index rows just sent: the next delivery sends only what differs from these.
    if (out / "index-hashes.json").exists():
        shutil.copyfile(out / "index-hashes.json", data / INDEX_HASHES)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["build", "commit"])
    ap.add_argument("--data", type=Path, default=ROOT / "data")
    ap.add_argument("--out", type=Path, required=True, help="directory for the SQL files (replaced)")
    ap.add_argument("--index", action="store_true", help="also upload the person-score index if it changed")
    ap.add_argument("--index-only", action="store_true",
                    help="only the person-score index, with the whole of today's budget (manual crawler run)")
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
    report = build(a.data, a.out, datetime.date.fromisoformat(a.today), a.index, budget, **({"index_only": True} if a.index_only else {}))
    day = FT.today()
    FT.d1_spend(a.data, report["writes"])
    report["d1_left_today"] = FT.d1_left(a.data)
    # 入れ終えたら commit が D1 の数に置き換える（足した日と見積もり。日をまたいでも足した日を直す）
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "spent.json").write_text(json.dumps({"day": day, "writes": report["writes"]}), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
