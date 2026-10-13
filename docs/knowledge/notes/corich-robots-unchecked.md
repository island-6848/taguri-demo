---
id: corich-robots-unchecked
type: finding
status: unverified
date: 2026-10-12
title: 取得元の実際の robots.txt はまだ読めていない
links:
  - raises: q-source-terms
verifies:
  - S24
---
作業環境の通信の制限で、CoRich などの robots.txt を取りに行けなかった。取得処理は実行時に robots.txt に従うが、内容そのものは確かめていない。
