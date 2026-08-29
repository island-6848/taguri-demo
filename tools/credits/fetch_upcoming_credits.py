#!/usr/bin/env python3
"""これから観られる公演から、裏方のクレジットを取れるか測る（V29）。

## なぜ過去と分けて測るのか

[検証 007](../../docs/verification/007-backstage-credits.md) で、**過去の公演では 33% が
URL に到達できなかった。公演が終わるとサイトが畳まれるためである。** 一方、システムが
推薦の候補として扱うのは**上演前・上演中の公演**で、そちらはサイトが生きている。

**名簿を作る側（過去の履歴）と、推薦の理由として照合する側（未来の候補）で条件が違う。**
過去の数字で候補側を判断すると、取得できるものを取得できないと誤って結論する。

## 取得元

ステイジーズカレンダー（公開の Google スプレッドシート）の「リンク」列。
**企画書が候補側で使うと決めている経路そのもの**を測る。
標本は**等間隔で抜く**（先頭に偏らせない）。1 リクエスト/秒以下。

    python3 tools/credits/fetch_upcoming_credits.py --run --sample 60
"""

from __future__ import annotations

import argparse
import collections
import csv
import datetime
import io
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_official_credits import (BACKSTAGE, ALL_ROLES, get, to_text,  # noqa: E402
                                    roles_in, links)

OUT = ROOT / "data" / "credits" / "upcoming.jsonl"
SHEET = "1OtXzChuCUfy2AnyuRW5ZgnMbsKHUwlCEF9keTA0Gb8c"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET}/export?format=csv&gid=0"


def parse_date(s: str):
    for f in ("%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.datetime.strptime(s.strip(), f).date()
        except ValueError:
            pass
    return None


def load(today: datetime.date) -> list[dict]:
    with urllib.request.urlopen(CSV_URL, timeout=60) as r:
        rows = list(csv.reader(io.StringIO(r.read().decode("utf-8"))))
    hdr = rows[1]
    col = {n: hdr.index(n) for n in ("劇場名", "公演団体名", "初日", "楽日", "リンク")}
    out = []
    for r in rows[2:]:
        if not r or not r[0].strip().isdigit():
            continue
        end = parse_date(r[col["楽日"]])
        url = r[col["リンク"]].strip()
        if end and end >= today and url.startswith("http"):
            out.append({"troupe": r[col["公演団体名"]].strip(),
                        "venue": r[col["劇場名"]].strip(),
                        "start": r[col["初日"]].strip(), "url": url})
    return out


def run(sample: int, today: str) -> None:
    day = datetime.date.fromisoformat(today)
    rows = load(day)
    print(f"まだ観られる公演: {len(rows)} 件")
    step = max(1, len(rows) // sample)
    picked = rows[::step][:sample]          # **等間隔で抜く**
    print(f"等間隔で {len(picked)} 件を標本にします（{step} 件ごと）…", flush=True)

    results = []
    for n, r in enumerate(picked, 1):
        html, err = get(r["url"])
        got, depth = {}, 0
        if html:
            got = roles_in(to_text(html))
            if not any(k in got for k in BACKSTAGE):
                for u2 in links(html, r["url"]):
                    h2, _ = get(u2)
                    if not h2:
                        continue
                    g2 = roles_in(to_text(h2))
                    if any(k in g2 for k in BACKSTAGE):
                        got, depth = g2, 1
                        break
        text_len = len(to_text(html)) if html else 0
        results.append({**r, "error": err, "depth": depth,
                        "text_len": text_len, "roles": got})
        print(f"  {n}/{len(picked)}", end="\r", flush=True)

    OUT.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in results),
                   encoding="utf-8")
    report(results)


def report(results=None) -> None:
    if results is None:
        results = [json.loads(l) for l in OUT.read_text(encoding="utf-8").split("\n") if l.strip()]
    n = len(results)
    cats: collections.Counter = collections.Counter()
    for r in results:
        if r["error"]:
            cats["到達できない"] += 1
        elif any(k in r["roles"] for k in BACKSTAGE):
            cats["裏方が取れた"] += 1
        elif r["text_len"] < 500:
            cats["JS 描画"] += 1
        elif not any(k in r for k in ()):   # 語の有無は本文を持たないので簡略化
            cats["裏方が取れない"] += 1
    print(f"\n■ 標本 {n} 件（まだ観られる公演・等間隔抽出）")
    for k, v in cats.most_common():
        print(f"   {v:>3} 件 ({v / n * 100:>3.0f}%)  {k}")
    back = cats["裏方が取れた"]
    print(f"\n   **裏方が 1 つ以上取れた {back}/{n} = {back / n * 100:.0f}%** ← V29 の判定")
    srv = n - cats["到達できない"] - cats["JS 描画"]
    if srv:
        print(f"   到達できてサーバ描画のページに限ると {back}/{srv} = {back / srv * 100:.0f}%")
    print("\n■ 役職別")
    for k in ALL_ROLES:
        c = sum(1 for r in results if k in r["roles"])
        if c:
            print(f"   {k:<8} {c:>3} 件  {c / n * 100:>3.0f}%")
    print("\n※ 人名は表示しない（V24 を測れなくしないため）")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--sample", type=int, default=60)
    ap.add_argument("--today", default="2026-08-20")
    a = ap.parse_args()
    if a.run:
        run(a.sample, a.today)
    elif a.report:
        report()
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
