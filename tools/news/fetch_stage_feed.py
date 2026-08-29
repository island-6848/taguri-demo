#!/usr/bin/env python3
"""ステージナタリーの Atom フィードから、公演の解禁記事を取れるか測る。

## なぜフィードを使うのか

**スクレイピングをしない。** ステージナタリーは Atom フィードを公開しているので、
HTML を解析せずに記事の題名・要約・URL・日時が取れる。提供側が配信を意図している
経路なので利用条件が明確で、書式も変わりにくい。

    https://natalie.mu/stage/feed/news

## 何のために使うのか

ステイジーズカレンダー（母集団）は**月末更新**なので、更新のあいだに発表された公演は
次の更新まで載らない。舞台は発表が早く、上演の数か月前に情報が解禁されるため、
**フィードは「カレンダーより早く気づく」経路**として使う。網羅はカレンダーが担う。

## 測る値

- 1 回の取得で得られるエントリ数と、**フィードが保持している期間**（週 1 回の起動で
  取りこぼしが出るかどうかが、これで決まる）
- 要約に上演時期・劇場が書かれている割合（記事だけで候補を作れるか）
- **記事が出た日から上演が始まるまでの日数**（＝発表を知った場合の猶予。上演日数の中央値
  4 日と対比するための数字）

## 同じ公演の記事が何度も出ることに注意する

1 つの公演について、**初報のあとにキャストの追加・ビジュアル解禁・開幕レポートと、
何度も記事が出る。** そのため次の 2 つを分けて扱う。

- **開幕・上演中の記事は、猶予の計算から外す。** 猶予がほぼ 0 なので混ぜると中央値が短く出る
- **発表・追加の記事にも、初報と追加情報が混ざる。** 追加情報は初報より上演に近いので、
  ここで出る猶予は**初報の猶予の下限**である。初報を特定するにはフィードを蓄積して
  同じ公演の記事をまとめる必要があり、直近 3 日ぶんの取得では判定できない
- 登録した名前（`--names`）が題名・要約に現れる件数

    python3 tools/news/fetch_stage_feed.py
    python3 tools/news/fetch_stage_feed.py --names 作り手17,劇団6,作り手1
"""

from __future__ import annotations

import argparse
import collections
import datetime
import re
import statistics
import urllib.request
import xml.etree.ElementTree as ET

FEED = "https://natalie.mu/stage/feed/news"
# 開幕・上演中の記事を見分ける語。これらは猶予がほぼ 0 なので、猶予の集計から外す。
STAGE_WORDS = ("開幕", "初日", "レポート", "会見", "ゲネプロ", "囲み", "上演中", "閉幕", "千秋楽")
NS = {"a": "http://www.w3.org/2005/Atom"}
UA = {"User-Agent": "Mozilla/5.0 (taguri feed reader)"}


def text(node, tag: str) -> str:
    return (node.findtext("a:" + tag, namespaces=NS) or "").strip()


def entries(raw: bytes) -> list[dict]:
    root = ET.fromstring(raw)
    out = []
    for e in root.findall("a:entry", NS):
        link = e.find("a:link", NS)
        out.append(dict(
            title=text(e, "title"),
            summary=text(e, "summary") or text(e, "content"),
            updated=text(e, "updated"),
            url=(link.get("href") if link is not None else ""),
        ))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--names", default="", help="照合する名前をカンマ区切りで")
    a = ap.parse_args()

    raw = urllib.request.urlopen(urllib.request.Request(FEED, headers=UA), timeout=30).read()
    es = entries(raw)
    days = collections.Counter(e["updated"][:10] for e in es)
    span = (datetime.date.fromisoformat(max(days)) - datetime.date.fromisoformat(min(days))).days + 1

    print(f"エントリ数        {len(es)} 件")
    print(f"保持している期間   {min(days)} 〜 {max(days)}（{span} 日）"
          f" → 1 日あたり約 {len(es) / span:.0f} 件")
    print(f"週 1 回の起動      {'取りこぼしが出る' if span < 7 else '取りこぼさない'}"
          f"（7 日ぶんを保持していないため）" if span < 7 else "")

    has_date = sum(1 for e in es if re.search(r"\d+月\d+日|来年|今年", e["summary"]))
    has_hall = sum(1 for e in es if re.search(r"劇場|ホール|シアター|THEATER|Theatre", e["summary"]))
    print(f"要約に上演時期あり {has_date}/{len(es)}")
    print(f"要約に劇場名あり   {has_hall}/{len(es)}")

    # 記事の配信日から上演開始までの日数。要約の最初の日付表現を上演時期とみなす。
    # 開幕・上演中の記事は猶予がほぼ 0 なので、分けて数える。
    leads, staged = [], []
    for e in es:
        pub = datetime.date.fromisoformat(e["updated"][:10])
        m = re.search(r"(来年|翌年)?\s*(\d{1,2})月(\d{1,2})?日?", e["summary"] + " " + e["title"])
        if not m:
            continue
        nxt, mo, dy = m.group(1), int(m.group(2)), int(m.group(3) or 1)
        if not (1 <= mo <= 12 and 1 <= dy <= 31):
            continue
        year = pub.year + (1 if nxt or mo < pub.month else 0)
        try:
            start = datetime.date(year, mo, dy)
        except ValueError:
            continue
        if any(w in e["title"] for w in STAGE_WORDS):
            staged.append((start - pub).days)
        else:
            leads.append((start - pub).days)
    if leads:
        print()
        print(f"上演までの猶予     発表・追加の記事 {len(leads)} 件（開幕・上演中の"
              f"{len(staged)} 件を除く）、中央値 {statistics.median(leads):.0f} 日"
              f"（最小 {min(leads)}／最大 {max(leads)}）")
        for lo, hi, lab in [(None, 0, "既に始まっている"), (1, 29, "1 か月未満"),
                            (30, 89, "1〜3 か月"), (90, None, "3 か月以上")]:
            c = sum(1 for x in leads
                    if (lo is None or x >= lo) and (hi is None or x <= hi))
            print(f"  {lab:9} {c:3} 件 {c / len(leads):4.0%}")
        if staged:
            print(f"  除いた開幕・上演中の記事 {len(staged)} 件は中央値 "
                  f"{statistics.median(staged):.0f} 日（拾っても間に合わない）")
        print("  ※ 発表・追加の記事にも初報と追加情報が混ざる。追加情報は初報より上演に"
              "近いので、この中央値は初報の猶予の下限である")

    # 同じ公演について何本の記事が出ているか（題名らしい語で畳んでみる）
    titles = collections.Counter()
    for e in es:
        m = re.findall(r"[「『]([^」』]{2,40})[」』]", e["title"] + " " + e["summary"])
        if m:
            titles[m[0]] += 1
    dup = {k: c for k, c in titles.items() if c > 1}
    print()
    print(f"題名らしい語が取れた記事 {sum(titles.values())}/{len(es)} 件、"
          f"同じ題名が複数回: {len(dup)} 題名")
    if not dup:
        print("  ※ 3 日ぶんでは重複が観測されない。同じ公演の記事は数週間おきに出るため、"
              "重複の実態はフィードを蓄積してからでないと測れない")

    names = [n.strip() for n in a.names.split(",") if n.strip()]
    if names:
        print()
        for n in names:
            hit = [e for e in es if n in e["title"] or n in e["summary"]]
            print(f"  {n}: {len(hit)} 件" + (f" ── {hit[0]['title'][:40]}" if hit else ""))

    print()
    print("直近の 5 件:")
    for e in es[:5]:
        print(f"  {e['updated'][:10]}  {e['title'][:56]}")


if __name__ == "__main__":
    main()
