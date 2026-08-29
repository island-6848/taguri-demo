#!/usr/bin/env python3
"""取得に失敗した公演ページについて、消滅かどうかを外から確かめる（検証 040）。

    python3 tools/stages/probe_dead_pages.py

URL ごとに 3 つを見る ── ホスト名が DNS で引けるか／その URL のステータス／
同じホストのトップのステータス。トップが 200 で URL が 404 なら、
サイトは生きていて公演ページだけが消えている。
取得の間隔は 1 秒に 1 リクエストとする（企画書 5 章の方針）。
"""

import json
import socket
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data/credits/official.jsonl"
UA = {"User-Agent": "Mozilla/5.0 (taguri verification; 1 req/sec)"}


def status(url: str):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as f:
            return f.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:
        return f"{type(e).__name__}"


def main() -> None:
    urls: dict[str, dict] = {}
    # **splitlines() を使わない。** U+2028（行区切り）でも分割してしまい、
    # json.dumps(ensure_ascii=False) はこれを escape しないため、1 レコードが割れる
    for line in SRC.read_text().split("\n"):
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("url") and r.get("error"):
            urls.setdefault(r["url"], r)

    print(f"取得に失敗した URL: {len(urls)} 件\n")
    for url, r in urls.items():
        host = urlsplit(url).hostname
        try:
            dns = socket.gethostbyname(host)
        except Exception:
            dns = "引けない"
        page = status(url)
        time.sleep(1)
        top = status(f"{urlsplit(url).scheme}://{host}/")
        time.sleep(1)
        verdict = ("ページだけ消えた" if page == 404 and top == 200
                   else "ドメインごと消えた" if dns == "引けない"
                   else "判定できない")
        print(f"{r['title'][:28]:30s} DNS={dns:18s} ページ={str(page):14s} トップ={str(top):14s} {verdict}")
        print(f"    {url}")


if __name__ == "__main__":
    main()
