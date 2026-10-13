#!/usr/bin/env python3
"""公開版のカタログが古くなっていないかを、公開の `/api/health` で確かめる。

    python3 tools/taguri/check_catalog_age.py                       # デモ版（Render）を見る
    python3 tools/taguri/check_catalog_age.py --url https://.../api/health --max-days 3

S3 に入れなくても、公開サーバーが返す日付（`catalog_info`）でカタログの古さが分かる。
いちばん新しい手がかり（S3 に置かれた時刻・カタログの中の最新ファイル・公演一覧を取り直した日）が
`--max-days` より古い、またはこれからの公演が `--min-upcoming` 件より少なければ、終了コード 1。
GitHub Actions（`.github/workflows/catalog-age.yml`）が毎日これを流し、失敗したら持ち主に通知が届く。
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
import time
import urllib.error
import urllib.request

DEFAULT_URL = "https://taguri-demo.onrender.com/api/health"
UA = "taguri-catalog-age-check/1.0 (+https://github.com/island-6848/taguri-demo)"
JST = datetime.timezone(datetime.timedelta(hours=9))


def fetch(url: str, tries: int = 3, timeout: int = 90) -> dict:
    """無料プランのサーバーは眠っていると起きるのに 1 分ほどかかるので、待って数回やり直す。"""
    last: Exception | None = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last = e
            if i + 1 < tries:
                time.sleep(20)
    raise RuntimeError(f"{url} を読めなかった（{type(last).__name__}）")


def judge(catalog: dict, today: datetime.date, max_days: int, min_upcoming: int) -> list[str]:
    """問題があれば、その説明の一覧（無ければ空）。"""
    problems = []
    if not catalog.get("present"):
        return ["カタログが入っていない（または、この版のサーバーは日付を返さない）"]
    dates = [catalog.get(k) for k in ("uploaded_at", "newest_file", "scan_date") if catalog.get(k)]
    if not dates:
        problems.append("カタログの日付の手がかりが無い（日付を残す前の取り込みのまま。サーバーを再起動すると付く）")
    else:
        newest = max(d[:10] for d in dates)
        age = (today - datetime.date.fromisoformat(newest)).days
        if age > max_days:
            problems.append(f"カタログが古い: いちばん新しい手がかりが {newest}（{age} 日前。上限 {max_days} 日）")
    up = (catalog.get("upcoming") or {}).get("candidates", 0)
    if up < min_upcoming:
        problems.append(f"これからの公演が少ない: {up} 件（下限 {min_upcoming} 件）")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--max-days", type=int, default=3, help="これより古ければ失敗（毎日更新なら 3 日で十分気付ける）")
    ap.add_argument("--min-upcoming", type=int, default=100, help="これからの公演がこれより少なければ失敗")
    a = ap.parse_args()
    try:
        health = fetch(a.url)
    except RuntimeError as e:
        print(e)
        return 2
    catalog = health.get("catalog") or {}
    print(json.dumps({"catalog": catalog}, ensure_ascii=False, indent=1))
    problems = judge(catalog, datetime.datetime.now(JST).date(), a.max_days, a.min_upcoming)
    for p in problems:
        print("NG: " + p)
    if not problems:
        print("OK: カタログは新しい")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
