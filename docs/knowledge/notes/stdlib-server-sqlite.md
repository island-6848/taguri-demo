---
id: stdlib-server-sqlite
type: finding
status: confirmed
date: 2026-10-13
title: サーバーは標準ライブラリの http.server と sqlite3 で書いてある
sources:
  - tools/taguri/serve.py
  - tools/review/rate_performances.py
links:
  - supports: dec-defer-workers
  - supports: dec-vm-cloudflare
  - answers: q-workers-free-viable
---
Workers は要求ごとに関数を呼ぶ形で、D1 には専用の呼び出し方でしか届かない。移すにはサーバーと DB まわりの書き直しが要る。
