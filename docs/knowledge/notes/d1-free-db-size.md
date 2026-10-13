---
id: d1-free-db-size
type: finding
status: unverified
date: 2026-10-13
title: D1 の無料プランは 1 つのデータベースが 500MB まで（二次情報）
sources:
  - https://cdn.jsdelivr.net/npm/memory-journal-mcp@8.0.1/skills/cloudflare/references/d1/README.md
links:
  - affects: scale-1000-estimate
verifies:
  - S21
---
有料は 1 つ 10GB まで、という整理が二次情報にある。公式の上限の表では確かめていない。1000 人分の記録と推薦の索引を 1 つに入れると届くかもしれない。
