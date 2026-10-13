---
id: dec-polite-crawling
type: decision
status: adopted
date: 2026-10-12
title: 取得はすべて polite_http を通す
sources:
  - docs/crawler-policy.md
links:
  - affects: comp-crawler
verifies:
  - S15
  - S24
---
サーバー攻撃だと思われないよう、取得の作法を 1 か所にまとめた。訪問者の操作では外部を検索しない。
