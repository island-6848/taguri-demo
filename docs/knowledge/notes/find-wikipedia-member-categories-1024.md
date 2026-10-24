---
id: find-wikipedia-member-categories-1024
type: finding
status: unverified
date: 2026-10-24
title: 日本語版 Wikipedia の分類から、宝塚歌劇団の在団・退団者（宝塚歌劇団N期生）と STARTO・旧ジャニーズの人物の名前を集める（集計中）
sources:
  - https://ja.wikipedia.org/w/api.php
links:
  - affects: dec-member-affil-tag
  - depends_on: q-affil-external-list
---
起案者の答え「b,c でお願い」（2026-10-24）の b（Wikipedia）。

- 宝塚: 「宝塚歌劇団N期生」の分類が 1〜112 期まで 112 ある（MediaWiki の API の allcategories で確かめた）。記事のある人だけが入る。
- STARTO: 「STARTO ENTERTAINMENT所属者」「ジャニーズ事務所の人物」「ジャニーズJr.」の分類（下の分類は 2 段まで）。
- この環境の IP は Wikipedia の API に 429（Too Many Requests）で断られやすい。Retry-After に従い、1 回ごとに 5 秒あけて取っている。
- 集め終えたら、数と、手元の出演欄の名前と合った数をここに書く。
