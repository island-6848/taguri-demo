---
id: find-kageki-unreachable-1024
type: finding
status: confirmed
date: 2026-10-24
title: 宝塚歌劇の公式サイト（kageki.hankyu.co.jp）は、通信の許可を足した後も、このセッションからは TLS の途中で切れて読めない（海外の IP を断っているとみられる）
sources:
  - https://kageki.hankyu.co.jp/
links:
  - affects: dec-member-affil-tag
  - depends_on: q-affil-external-list
---
起案者が通信の許可に kageki.hankyu.co.jp を足した後（2026-10-24）に試した。

- 通信の仲介（proxy）までのトンネルは開く（`HTTP/1.1 200 Connection Established`）。その先の TLS のやり取りの途中で切れ、`ws_closed_mid_exchange` になる。トップページも robots.txt も読めない。
- 同じ時に starto.jp と ja.wikipedia.org は読めた。Wikipedia の応答では、こちらの IP は米国（GeoIP=US）と出た。
- 公式サイトが日本の外からの接続を断っているとみられる（unverified: サイトの説明は読めていない）。回り道はしない。
- そのため、宝塚の在団・退団の一覧は Wikipedia の分類〔find-wikipedia-member-categories-1024〕と、手元の公演の出演欄だけで作る。
