---
id: robotparser-decimal-delay
type: finding
status: confirmed
date: 2026-10-12
title: Python の robotparser は小数の Crawl-delay を読めない
sources:
  - tools/lib/polite_http.py
  - tools/lib/test_polite_http.py
links:
  - affects: comp-crawler
---
`Crawl-delay: 1.5` が無視されるので、取得の作法では自前で読んでいる。
