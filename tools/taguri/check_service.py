#!/usr/bin/env python3
"""サービス版（Cloudflare Worker）が動いているかを外から確かめる（S22、q-monitoring）。

    python3 tools/taguri/check_service.py --url https://<Worker の URL>/api/health

見るもの（どれも公開の入口だけ。利用者の記録には触れない）:
- `/api/health` が 200 で `ok: true` を返す（D1 を読むので、D1 が止まっていても分かる）
- 未ログインで開ける画面（`/about`・`/login`）が 200
- それぞれ `--slow` 秒より遅くない
- 無料枠の数え（health の `free_tier`）が上限の 8 割を越えていない

問題があれば終了コード 1。GitHub Actions（`.github/workflows/service-watch.yml`）が 1 時間ごとに流し、
失敗したらリポジトリの持ち主に GitHub から通知が届く。一度だけの通信の失敗で鳴らないよう、2 回まで
やり直す。
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request

UA = "taguri-service-watch/1.0 (+https://github.com/island-6848/taguri-demo)"
PAGES = ("/about", "/login")


def get(url: str, timeout: float) -> tuple[int, bytes, float]:
    """(status, body, seconds)。通信の失敗は status 0。"""
    t = time.monotonic()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(), time.monotonic() - t
    except urllib.error.HTTPError as e:
        return e.code, b"", time.monotonic() - t
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0, b"", time.monotonic() - t


def check_once(base: str, slow: float, fetch=get) -> list[str]:
    problems = []
    status, body, sec = fetch(base + "/api/health", 30)
    if status != 200:
        problems.append(f"/api/health が {status or '応答なし'}")
    else:
        try:
            health = json.loads(body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            health = {}
        if health.get("ok") is not True:
            problems.append("/api/health が ok を返さない")
        ft = health.get("free_tier") or {}
        reads, cap = ft.get("r2_reads_month"), ft.get("r2_reads_cap")
        if isinstance(reads, int) and isinstance(cap, int) and cap > 0 and reads >= 0.8 * cap:
            problems.append(f"R2 の読み出しが今月 {reads:,} 回（上限 {cap:,} の 8 割を越えた）")
        if sec > slow:
            problems.append(f"/api/health が遅い（{sec:.1f} 秒）")
    for page in PAGES:
        status, _, sec = fetch(base + page, 30)
        if status != 200:
            problems.append(f"{page} が {status or '応答なし'}")
        elif sec > slow:
            problems.append(f"{page} が遅い（{sec:.1f} 秒）")
    return problems


def check(base: str, slow: float = 10.0, tries: int = 3, wait: float = 30.0, fetch=get, sleep=time.sleep) -> list[str]:
    """やり直しても残った問題の一覧（無ければ空）。"""
    problems: list[str] = []
    for i in range(tries):
        problems = check_once(base, slow, fetch)
        if not problems:
            return []
        if i + 1 < tries:
            sleep(wait)
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", required=True, help="health の URL（https://…/api/health）")
    ap.add_argument("--slow", type=float, default=10.0, help="これより遅ければ問題（秒）")
    a = ap.parse_args()
    base = a.url.rstrip("/")
    if base.endswith("/api/health"):
        base = base[: -len("/api/health")]
    problems = check(base, a.slow)
    for p in problems:
        print("NG: " + p)
    if not problems:
        print("OK: サービス版は動いている")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
