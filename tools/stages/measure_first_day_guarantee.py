#!/usr/bin/env python3
"""「初日までに必ず 1 回出す」を保証できるかを、母集団の実データで測る。

## なぜ初日で測るのか

企画書は締切を「買える最終期限（前売の締切・完売・楽日のうち最も早いもの）」で
持つと書いているが、**母集団にその列は無い。** 実際に取れるのは

- **初日と楽日** ── CoRich の一覧の「期間」から 100% 取れる
- **発売日** ── 料金欄の【発売日】から 82% 取れる（欠ける 18% は保証に使えない）

したがって**全件について観測できる期限は初日だけ**である。起案者の判断で、
保証の期限を「買える窓が閉じる時点」から**「初日」**に置き直す。

## 測る値

1. **必要な週あたりの提示件数** ── 未提示のまま初日を越える公演を 0 にするには、
   週に何件を本体に出す必要があるか（現在の在庫を初日順に掃く形で計算する）
2. **1 日ぶんの流入** ── 前日の取得と当日の取得を突き合わせ、新しく母集団に
   現れた公演の初日がいつかを見る。**初日を過ぎてから現れたものは、
   どんな設計でも初日までに出せない**（保証の上限そのもの）

    python3 tools/stages/measure_first_day_guarantee.py            # 在庫だけで計算
    python3 tools/stages/measure_first_day_guarantee.py --fetch    # 当日の一覧も取る
"""

from __future__ import annotations

import argparse
import datetime
import gzip
import json
import re
import statistics
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "review"))
from fetch_candidates import ROW, pick, txt, period_end   # noqa: E402

SNAP = ROOT / "data" / "review" / "candidates.jsonl"
BASE = "https://stage.corich.jp"
UA = "taguri-verification/0.1 (personal use; 1 req/sec)"
_last = [0.0]


def fetch(url: str, cache: Path) -> str:
    """**この測定では既存のキャッシュを使わない。** 前日の HTML が返ると差分が取れない。"""
    key = cache / (re.sub(r"[^A-Za-z0-9]", "_", url)[-120:] + ".html")
    if key.exists():
        return key.read_text(encoding="utf-8")
    wait = 1.1 - (time.monotonic() - _last[0])
    if wait > 0:
        time.sleep(wait)
    _last[0] = time.monotonic()
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=45) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        html = raw.decode("utf-8", "replace")
    cache.mkdir(parents=True, exist_ok=True)
    key.write_text(html, encoding="utf-8")
    return html


def listing(page: int, frm: datetime.date, cache: Path) -> list[dict]:
    q = urllib.parse.urlencode({
        "search": 1, "sort": "start_asc", "page": page,
        "stage[start_date(1i)]": frm.year,
        "stage[start_date(2i)]": frm.month,
        "stage[start_date(3i)]": frm.day,
    })
    html = fetch(f"{BASE}/stage/search?{q}", cache)
    rows, seen = [], set()
    for sid, block in ROW.findall(html):
        if sid in seen:
            continue
        seen.add(sid)
        period = pick(block, "period")
        rows.append({
            "stage_id": sid,
            "title": pick(block, "stage"),
            "group": pick(block, "group"),
            "period": re.sub(r"(公演)?(開幕前|上演中|終了)$", "", period).strip(),
        })
    return rows


def opening(period: str):
    ms = re.findall(r"(20\d\d)/(\d{1,2})/(\d{1,2})", period or "")
    if not ms:
        return None
    y, m, d = ms[0]
    return datetime.date(int(y), int(m), int(d))


def required_per_week(opens: list[datetime.date], today: datetime.date) -> None:
    """初日順に掃くとき、未提示のまま初日を越えさせないための週あたり件数。

    週 w までに初日が来る件数を cum(w) とすると、w+1 週かけて掃くので
    必要な件数は max over w の cum(w)/(w+1) になる。
    """
    fut = sorted(d for d in opens if d >= today)
    weeks: dict[int, int] = {}
    for d in fut:
        weeks[(d - today).days // 7] = weeks.get((d - today).days // 7, 0) + 1
    cum, need = 0, []
    for w in sorted(weeks):
        cum += weeks[w]
        need.append((w, weeks[w], cum, cum / (w + 1)))
    print("  週 | その週に初日 | 累計 | 必要件数/週")
    for w, n, c, r in need[:12]:
        print(f"  {w:>2} | {n:>10} | {c:>4} | {r:>7.1f}")
    print(f"\n  → 在庫を掃くのに必要なのは 週 {max(r for *_, r in need):.0f} 件")
    print(f"  → 定常の流入は 週 {statistics.median(n for _, n, _, _ in need[:6]):.0f} 件"
          f"（近い 6 週の中央値。先の週は登録がまだ薄いので使わない）")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fetch", action="store_true", help="当日の一覧を取って差分を測る")
    ap.add_argument("--today", default=str(datetime.date.today()))
    ap.add_argument("--snapshot-date", default="2026-08-20")
    ap.add_argument("--since-days", type=int, default=80)
    ap.add_argument("--pages", type=int, default=60)
    a = ap.parse_args()
    today = datetime.date.fromisoformat(a.today)
    snap_day = datetime.date.fromisoformat(a.snapshot_date)

    snap = [json.loads(l) for l in SNAP.open(encoding="utf-8")]
    snap_open = {r["stage_id"]: opening(r.get("period") or r["fields"].get("期間", ""))
                 for r in snap}
    got = sum(1 for v in snap_open.values() if v)
    print(f"■ 母集団 {len(snap)} 件（取得日 {snap_day}）")
    print(f"  初日が取れた: {got}/{len(snap)} = {got / len(snap):.0%}")
    fee = [r["fields"].get("料金（1枚あたり）", "") for r in snap]
    sale = sum(1 for f in fee
               if re.search(r"\d{1,2}\s*[/月]\s*\d{1,2}",
                            (re.search(r"【発売日】(.{0,80})", f, re.S) or
                             re.match(r"(?!)", "")).group(1) if re.search(r"【発売日】", f) else ""))
    print(f"  発売日が取れた: {sale}/{len(snap)} = {sale / len(snap):.0%}"
          f"  ← 保証の期限には使えない（欠ける分がある）")

    print(f"\n■ 初日までに 1 回出すために必要な件数（基準日 {snap_day}）")
    required_per_week([v for v in snap_open.values() if v], snap_day)

    if not a.fetch:
        return 0

    print(f"\n■ {today} の一覧を取り直して、1 日ぶんの流入を測る")
    cache = ROOT / "data" / "stages" / f"listing_{today:%Y%m%d}"
    frm = today - datetime.timedelta(days=a.since_days)
    cur: dict[str, dict] = {}
    for p in range(1, a.pages + 1):
        rows = listing(p, frm, cache)
        if not rows:
            break
        for r in rows:
            cur.setdefault(r["stage_id"], r)
        print(f"  一覧 {p} ページ目 / 走査 {len(cur)} 件", end="\r", flush=True)
    print(f"\n  当日の一覧: {len(cur)} 件（楽日で絞る前）")

    alive = {sid: r for sid, r in cur.items()
             if (period_end(r["period"]) or today) >= today}
    new = [r for sid, r in alive.items() if sid not in snap_open]
    print(f"  楽日が今日以降: {len(alive)} 件 / うち前日に無かった新規: {len(new)} 件")

    late = [r for r in new if (opening(r["period"]) or today) < today]
    soon = [r for r in new if today <= (opening(r["period"]) or today)
            <= today + datetime.timedelta(days=7)]
    print(f"  新規のうち **初日を過ぎてから現れた**: {len(late)} 件"
          f"  ← どんな設計でも初日までに出せない")
    print(f"  新規のうち 初日が 7 日以内: {len(soon)} 件")
    for r in new[:15]:
        o = opening(r["period"])
        print(f"    {o} {r['group'][:14]:<14} {r['title'][:34]}")
    out = ROOT / "data" / "stages" / f"inflow_{today:%Y%m%d}.json"
    out.write_text(json.dumps({
        "取得日": str(today), "前日の母集団": len(snap), "当日の一覧": len(alive),
        "新規": [{"stage_id": r["stage_id"], "初日": str(opening(r["period"])),
                  "団体": r["group"], "題名": r["title"]} for r in new],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  → {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
