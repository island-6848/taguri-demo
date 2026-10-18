---
id: q-workers-builds-minutes
type: question
status: open
date: 2026-10-18
title: Workers Builds の月の分を誰が見るか（数える仕組みが無い）
links:
  - depends_on: free-tier-audit-1018
  - affects: workers-builds-free-3000
---
Workers Builds は無料で月 3,000 分。master に押すたびに 1 回 1〜2 分。2026-10-01〜18 は master の first-parent のコミットが 347（1 日 約 19 回）で、月 約 570〜1,180 分の見込み。1 日 50 回を越えて押すと越えうる。越えたら止まるのか請求されるのかは未確認（workers-builds-free-3000）。リポジトリからは分数を読めないので、起案者がダッシュボードで月の分を見るか、押す回数をまとめる。
