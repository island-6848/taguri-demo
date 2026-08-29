#!/usr/bin/env python3
"""当事者が通う劇場の公式サイトに、**公式に配信されている経路**があるかを調べる。

母集団（CoRich・ステイジーズカレンダー）は劇場の公式サイトを標本にすると 81% しか
覆えていない（[検証 025](../../docs/verification/025-venue-coverage.md)）。残る 19% を
埋めるのに**スクレイピングを増やしたくない**ので、まず「提供側が配信を意図している
経路」（RSS・Atom・sitemap）があるかを館ごとに数える。

    python3 tools/stages/probe_venue_feeds.py
"""

from __future__ import annotations

import gzip
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "stages" / "venue_feeds.json"
UA = "taguri-verification/0.1 (personal use; 1 req/sec)"

# 検証 017 で「当事者が通う劇場」として数えた館（首都圏で営業中の 8 館）＋ 東京芸術劇場
VENUES = {
    "劇場3": "https://www.nntt.jac.go.jp",
    "吉祥寺シアター": "https://www.musashino-culture.or.jp",
    "本多劇場": "https://www.honda-geki.com",
    "日生劇場": "https://www.nissaytheatre.or.jp",
    "シアタークリエ": "https://www.tohostage.com",
    "明治座": "https://www.meijiza.co.jp",
    "劇場2": "https://setagaya-pt.jp",
    "東京芸術劇場": "https://www.geigeki.jp",
    "三越劇場": "https://mitsukoshi.mistore.jp",
}
PATHS = ["/feed", "/rss", "/feed/atom", "/sitemap.xml", "/wp-sitemap.xml", "/robots.txt"]
_last = [0.0]


def get(url: str):
    wait = 1.1 - (time.monotonic() - _last[0])
    if wait > 0:
        time.sleep(wait)
    _last[0] = time.monotonic()
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            raw = r.read(4000)
            if r.headers.get("Content-Encoding") == "gzip":
                try:
                    raw = gzip.decompress(raw)
                except Exception:
                    pass
            return r.status, r.headers.get("Content-Type", ""), raw.decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, "", ""
    except Exception as e:
        return None, type(e).__name__, ""


def main() -> int:
    res = {}
    for name, base in VENUES.items():
        found = []
        for p in PATHS:
            code, ctype, body = get(base + p)
            if code != 200:
                continue
            head = body[:400].lower()
            kind = ("feed" if ("<rss" in head or "<feed" in head or "<rdf" in head) else
                    "sitemap" if "<urlset" in head or "<sitemapindex" in head else
                    "robots" if p == "/robots.txt" else "html")
            if kind in ("feed", "sitemap"):
                found.append((p, kind))
            if kind == "robots":
                for line in body.splitlines():
                    if line.lower().startswith("sitemap:"):
                        found.append((line.split(":", 1)[1].strip(), "sitemap(robots)"))
        res[name] = found
        mark = "配信あり" if any(k == "feed" for _, k in found) else \
               "sitemap のみ" if found else "**無し**"
        print(f"  {name:<14} {mark}  {found}")
    n_feed = sum(1 for v in res.values() if any(k == "feed" for _, k in v))
    n_map = sum(1 for v in res.values() if v and not any(k == "feed" for _, k in v))
    print(f"\n  RSS/Atom を配信: {n_feed}/{len(VENUES)} 館")
    print(f"  sitemap だけ: {n_map}/{len(VENUES)} 館")
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  → {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
