#!/usr/bin/env python3
"""公演の「初報」がいつ出るかを、ステージナタリーの公演情報ページから測る。

## なぜ測るのか

企画書の効果 2 は「発表の時点で拾えるので猶予が伸びる」と主張している。その猶予を
フィード（直近 3 日ぶん・24 件）の中央値 35 日で書いていたが、**フィードに写るのは
初報だけでなくキャスト追加や開幕レポートも混ざる**ため、初報の猶予は測れていなかった。
実例 1 件（『管理人ご夫妻』＝162 日）しか無い状態を、標本を増やして置き換える。

## どう測るか

`natalie.mu/stage/play/N`（公演情報ページ）には次の 2 つが載っている。

- **公演期間** ── `NA_article_addition` の「2024年8月21日（水）～9月15日（日）」
- **その公演のニュース一覧** ── 見出しと、画像 URL に含まれる配信日（`.../2024/0410/...`）

**初報 = その公演のニュースのうち最も古いもの**とし、初日との差を猶予とする。

**同じページに別公演の記事が混ざる。** 例えば「日米合作 ブロードウェイミュージカル」の
ページには RENT（2024）とフル・モンティ（2026）の記事が並ぶ。そこで**公演名の特徴語
（題名の「」の中など）を見出しに含む記事だけ**を数える。

**それでも、同じ題名の再演や長期公演では前回公演の記事を初報と誤る。** 実測で 3 件出た
（『お気に入り63』は 2021 年の公演の記事で 2057 日、『ハリー・ポッターと呪いの子』は
初日が 2022 年の長期公演なので −1291 日）。**0 日以上 730 日以内に収まらないものは、
測定の失敗として除外し、件数を表示する。**

## 作法

- `robots.txt` を確認し、**`Disallow: /search` に従って検索は使わない。** 公演の一覧は
  閲覧が許可されている `/stage/play/list/page/N` から取る
- **1 リクエスト/秒**。取得したページは `data/natalie/play/` にキャッシュし、再実行では取り直さない

## 標本の偏り（結果を読むときの注意）

- **ナタリーが記事にした公演に限られる。** 小劇場の公演は載らないことが多い
- **一覧は注目度順**なので、**大型の商業公演に偏る。** 発表が早い側に偏る可能性が高い
- したがってここで出る猶予は、**カレンダー 1,056 件の代表値ではない**

    python3 tools/news/first_report_lead.py --n 50
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import statistics
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data/natalie/play"
UA = {"User-Agent": "Mozilla/5.0 (taguri research; 1 req/sec; contact via repository)"}
LIST_URL = "https://natalie.mu/stage/play/list/page/{}"
PLAY_URL = "https://natalie.mu/stage/play/{}"
WAIT = 1.0
# 初報として採る範囲。範囲外は「同じ題名の別公演の記事を拾った」と見て除外する。
LEAD_MIN, LEAD_MAX = 0, 730


def fetch(url: str, cache: Path | None) -> str:
    if cache and cache.exists():
        return cache.read_text(encoding="utf-8")
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        body = r.read().decode("utf-8", "replace")
    if cache:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(body, encoding="utf-8")
    time.sleep(WAIT)
    return body


def play_ids(pages: int) -> list[int]:
    ids: list[int] = []
    for i in range(1, pages + 1):
        html = fetch(LIST_URL.format(i), CACHE / f"list-{i}.html")
        for m in re.findall(r"/stage/play/(\d+)", html):
            if int(m) not in ids:
                ids.append(int(m))
    return ids


def first_day(html: str):
    m = re.search(r'class="NA_article_addition">(\d{4})年(\d{1,2})月(\d{1,2})日', html)
    if not m:
        return None
    y, mo, d = (int(x) for x in m.groups())
    try:
        return datetime.date(y, mo, d)
    except ValueError:
        return None


def title(html: str) -> str:
    m = re.search(r'class="NA_article_title">(.*?)</h1>', html, re.S)
    return re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else ""


def keywords(t: str) -> list[str]:
    """公演名の特徴語。「」の中を優先し、無ければ長い連続語を使う。"""
    inner = re.findall(r"[「『]([^」』]{2,30})[」』]", t)
    if inner:
        return inner
    words = re.split(r"[\s　・／/、,（）()【】\-−–—]+", t)
    words = [w for w in words if len(w) >= 3]
    return sorted(words, key=len, reverse=True)[:1]


def articles(html: str, keys: list[str]):
    """（配信日, 見出し）の一覧。その公演を指す記事だけに絞る。"""
    try:
        sec = html[html.index("のニュース"):html.index("の画像")]
    except ValueError:
        return []
    cards = re.findall(
        r'/stage/news/\d+".*?media/news/stage/(\d{4})/(\d{4})[^"]*"\s+alt="([^"]*)"',
        sec, re.S)
    out = []
    for y, md, alt in cards:
        if keys and not any(k in alt for k in keys):
            continue
        try:
            out.append((datetime.date(int(y), int(md[:2]), int(md[2:])), alt))
        except ValueError:
            pass
    return sorted(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=50, help="測る公演の数")
    a = ap.parse_args()

    ids = play_ids(pages=-(-a.n // 25))
    rows, skipped = [], {"初日なし": 0, "記事なし": 0}
    for pid in ids:
        if len(rows) >= a.n:
            break
        html = fetch(PLAY_URL.format(pid), CACHE / f"play-{pid}.html")
        day = first_day(html)
        if not day:
            skipped["初日なし"] += 1
            continue
        arts = articles(html, keywords(title(html)))
        if not arts:
            skipped["記事なし"] += 1
            continue
        rows.append(dict(id=pid, title=title(html), first_day=str(day),
                         first_report=str(arts[0][0]), lead=(day - arts[0][0]).days,
                         n_articles=len(arts)))

    dropped = [r for r in rows if not (LEAD_MIN <= r["lead"] <= LEAD_MAX)]
    rows = [r for r in rows if LEAD_MIN <= r["lead"] <= LEAD_MAX]
    leads = [r["lead"] for r in rows]
    print(f"測れた公演        {len(rows)} 件（初日なし {skipped['初日なし']} 件／"
          f"その公演の記事が取れず {skipped['記事なし']} 件／"
          f"再演や長期公演で範囲外 {len(dropped)} 件を除外）")
    for r in dropped:
        print(f"  除外 {r['lead']:6} 日  {r['title'][:38]}")
    if not leads:
        return
    print(f"初報から初日まで   中央値 {statistics.median(leads):.0f} 日"
          f"（最小 {min(leads)}／最大 {max(leads)}）")
    for lo, hi, lab in [(None, 0, "初日以降が初報"), (1, 29, "1 か月未満"),
                        (30, 89, "1〜3 か月"), (90, 179, "3〜6 か月"), (180, None, "6 か月以上")]:
        c = sum(1 for x in leads if (lo is None or x >= lo) and (hi is None or x <= hi))
        print(f"  {lab:12} {c:3} 件 {c / len(leads):4.0%}  {'█' * round(c / len(leads) * 40)}")
    arts = [r["n_articles"] for r in rows]
    print(f"1 公演あたりの記事数 中央値 {statistics.median(arts):.0f} 件"
          f"（最小 {min(arts)}／最大 {max(arts)}）")
    print()
    for r in sorted(rows, key=lambda r: -r["lead"])[:5] + sorted(rows, key=lambda r: r["lead"])[:3]:
        print(f"  {r['lead']:5} 日  初報 {r['first_report']} → 初日 {r['first_day']}"
              f"  記事 {r['n_articles']} 件  {r['title'][:34]}")
    out = ROOT / "data/natalie/first_report_lead.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n書き出し: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
