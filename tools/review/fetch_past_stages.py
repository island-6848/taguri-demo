#!/usr/bin/env python3
"""過去の公演の一覧を、CoRich の公演ページから少しずつ作る（記録を自動で結び付けるため）。

    python3 tools/review/fetch_past_stages.py --limit 6000 --since 2019-01-01
    python3 tools/review/fetch_past_stages.py --report

## なぜ要るのか

起案者の指示（2026-10-13）「いちいち結びつけなくても、過去の公演の情報紐づいてほしい」。
記録（観た日・題名）を公演ページに結び付けると、出演者・作り手・あらすじが記録に付き、
おすすめの材料にもなる。ところが手元にある公演の一覧は「これから」と「終わって 180 日以内」
（candidates.jsonl）だけで、それより古い公演は照合の相手がいない（docs/knowledge の
auto-link-current-state）。CoRich の検索ページはデータセンターからは断られる（corich-search-waf-403）
ので、サイトマップに載っている公演ページの番号を **新しいほうから** 1 枚ずつ読む。

## 決めたこと（q-auto-link-past・起案者の指示「2019年以降、1日6000件で進めて」）

- **範囲は 2019 年以降。** 番号は登録の順なので新しいほうから読み、会期の終わりが `--since` より前の
  ページが続けて `--stop-after` 枚出たら読み終わりとする（古い公演があとから登録されることもあるので、
  1 枚で止めない）
- **1 回に読むのは `--limit` 枚（既定 6,000）。** 取得の作法は polite_http（名乗り・robots.txt・
  同じホストへ 1.1 秒の間隔）に任せる。6,000 枚でおよそ 110 分
- **手元に置くのは照合とおすすめに要る分だけ:** 題名・会期・劇場・団体・都道府県と、出演・作り手の欄。
  **ページの HTML は残さない**（fetch_credits.get はページを data/credits/pages に溜めるが、ここでは
  使わない ── 数万枚を作業データに積むと state ブランチが膨らむ）。外へは配らない
  （catalog-terms-no-redistribution）
- 1 回で読み切れなくても、読んだところまでは `progress.json` に残る（途中で止まっても続きから読む）

## 作るもの

- `data/past/stages.jsonl` ── 1 公演 1 行（追記）。`{stage_id, title, period, start, end, group,
  theater, pref, fields}`。`start`・`end` は YYYY-MM-DD
- `data/past/progress.json` ── `{cursor, top, done, old_streak, read, skipped, updated}`。
  `cursor` は次に読む番号の上限（これより小さい番号を読む）
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools" / "credits"))
sys.path.insert(0, str(ROOT / "tools" / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_credits as FC                           # noqa: E402
import polite_http as PH                             # noqa: E402

PAST = ROOT / "data" / "past"
ROWS = PAST / "stages.jsonl"
PROGRESS = PAST / "progress.json"
CANDIDATES = ROOT / "data" / "review" / "candidates.jsonl"

# 照合とおすすめに使う欄だけを残す（料金・問い合わせなどは持たない）
KEEP_FIELDS = set(FC.ROLE_KEYS) | {"劇場", "スタッフ"}

_DATE = re.compile(r"(20\d\d)/(\d{1,2})/(\d{1,2})")


def span(period: str) -> tuple[str, str]:
    """会期の文字から (初日, 千秋楽) を YYYY-MM-DD で。読めなければ空文字。"""
    ds = []
    for y, m, d in _DATE.findall(period or ""):
        try:
            ds.append(date(int(y), int(m), int(d)).isoformat())
        except ValueError:
            continue
    if not ds:
        return "", ""
    return min(ds), max(ds)


def row_from_html(html: str, sid: str) -> dict:
    """公演ページ 1 枚から、手元に置く 1 行を作る（fetch_candidates.stage_row と同じ読み方）。"""
    import fetch_candidates as FCand
    c = FC.parse_stage(html, sid)
    f = c["fields"]
    mp = re.search(r'<span class="pref">(.*?)</span>', html, re.S)
    theater = re.sub(r"\(.*?\)$", "", FCand.pick(html, "theater")).strip()
    period = re.sub(r"\s*\([^)]*\)", "", c["period"] or "").replace("～", "〜").strip()
    start, end = span(period)
    import unicodedata
    return {
        "stage_id": str(sid),
        "title": unicodedata.normalize("NFKC", c["page_title"] or "").strip(),
        "period": period,
        "start": start,
        "end": end,
        "group": FCand.pick(html, "group"),
        "theater": theater or f.get("劇場", ""),
        "pref": FCand.txt(mp.group(1)).strip("()（）") if mp else "",
        "fields": {k: v for k, v in f.items() if k in KEEP_FIELDS and v},
    }


def load_progress() -> dict:
    if PROGRESS.exists():
        return json.loads(PROGRESS.read_text(encoding="utf-8"))
    return {"cursor": None, "top": None, "done": False, "old_streak": 0, "read": 0, "skipped": 0}


def save_progress(p: dict) -> None:
    PAST.mkdir(parents=True, exist_ok=True)
    p["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    tmp = PROGRESS.with_suffix(".part")
    tmp.write_text(json.dumps(p, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    tmp.replace(PROGRESS)


def known_ids() -> set[str]:
    """もう手元にある公演（読んだ過去の公演と、毎日の一覧にある公演）。読み直さない。"""
    out: set[str] = set()
    for path in (ROWS, CANDIDATES):
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    out.add(str(json.loads(line).get("stage_id") or ""))
                except ValueError:
                    continue
    out.discard("")
    return out


def plan(ids: list[int], progress: dict, known: set[str], limit: int) -> list[int]:
    """今回読む番号（新しいほうから `limit` 枚）。`cursor` より小さく、まだ手元に無いもの。"""
    cur = progress.get("cursor")
    out = []
    for i in sorted(ids, reverse=True):
        if cur is not None and i >= cur:
            continue
        if str(i) in known:
            continue
        out.append(i)
        if len(out) >= limit:
            break
    return out


def run(ids: list[int], *, limit: int, since: str, stop_after: int, max_minutes: float,
        fetch=None) -> dict:
    """読む。`fetch(sid) -> html` は試験で差し替える。戻り値は今回の数え。"""
    fetch = fetch or (lambda sid: PH.fetch(f"{FC.BASE}/stage/{sid}", timeout=45).decode("utf-8", "replace"))
    p = load_progress()
    if p.get("done"):
        return {"read": 0, "kept": 0, "skipped": 0, "done": True, "cursor": p.get("cursor")}
    if p.get("top") is None and ids:
        p["top"] = max(ids)
    todo = plan(ids, p, known_ids(), limit)
    t0 = time.monotonic()
    got = {"read": 0, "kept": 0, "skipped": 0, "old": 0}
    PAST.mkdir(parents=True, exist_ok=True)
    with ROWS.open("a", encoding="utf-8") as out:
        for n, sid in enumerate(todo, 1):
            if max_minutes and (time.monotonic() - t0) / 60 > max_minutes:
                print(f"時間の上限（{max_minutes} 分）に来たので、ここまでにする")
                break
            try:
                html = fetch(sid)
            except PH.Skipped as e:
                # ホストから手を引いた（robots.txt・429 が続いた等）なら、この実行はここまで
                print(f"取得をやめる: {e}")
                break
            except Exception as e:                    # 消えたページ・一時的な失敗は飛ばす
                got["skipped"] += 1
                p["skipped"] = p.get("skipped", 0) + 1
                p["cursor"] = sid
                print(f"{sid}: 読めなかった（{type(e).__name__}）")
                continue
            row = row_from_html(html, str(sid))
            got["read"] += 1
            p["read"] = p.get("read", 0) + 1
            p["cursor"] = sid
            if row["end"] and row["end"] < since:
                p["old_streak"] = p.get("old_streak", 0) + 1
                got["old"] += 1
            else:
                p["old_streak"] = 0
            if row["title"] and row["start"] and not (row["end"] and row["end"] < since):
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
                got["kept"] += 1
            if p["old_streak"] >= stop_after:
                p["done"] = True
                print(f"会期が {since} より前の公演が {stop_after} 枚続いたので、読み終わりとする")
                break
            if n % 100 == 0:
                out.flush()
                save_progress(p)
    if not todo:
        p["done"] = True
    save_progress(p)
    got.update(done=p.get("done", False), cursor=p.get("cursor"))
    return got


def report() -> None:
    p = load_progress()
    n = sum(1 for line in ROWS.read_text(encoding="utf-8").splitlines() if line.strip()) if ROWS.exists() else 0
    print(json.dumps({**p, "rows": n}, ensure_ascii=False, indent=1))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--limit", type=int, default=6000, help="1 回に読む公演ページの枚数")
    ap.add_argument("--since", default="2019-01-01", help="会期の終わりがこの日より前の公演は残さない")
    ap.add_argument("--stop-after", type=int, default=300,
                    help="--since より前の公演がこの枚数続いたら読み終わりとする")
    ap.add_argument("--max-minutes", type=float, default=0, help="この分数を過ぎたら止める（0 は無制限）")
    ap.add_argument("--report", action="store_true", help="今どこまで読んだかを出す")
    a = ap.parse_args()
    if a.report:
        report()
        return 0
    import fetch_candidates as FCand
    ids = FCand.sitemap_stage_ids()
    print(f"サイトマップの公演ページ: {len(ids)} 枚（最大の番号 {max(ids) if ids else '-'}）")
    got = run(ids, limit=a.limit, since=a.since, stop_after=a.stop_after, max_minutes=a.max_minutes)
    print(json.dumps(got, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
