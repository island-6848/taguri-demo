---
id: worker-reco-cpu-estimate
type: finding
status: unverified
date: 2026-10-13
title: Worker での推薦計算は 1 回 10〜12 ミリ秒、重い想定で 39 ミリ秒（見積もり）
sources:
  - https://github.com/island-6848/taguri-demo/blob/cloudflare-d1-preview/cloudflare/README.md
links:
  - contradicts: dec-defer-workers
  - raises: q-real-catalog-stats
  - affects: q-direction
verifies:
  - S20
---
もう一方の作業の手元での見積もり（公演 1,200・評価 100 で約 5,400 行・10〜12 ミリ秒。公演 3,000・評価 200 で約 3 万行・39 ミリ秒）。無料プランの 10 ミリ秒には重い想定で収まらない。計算し直すのは記録や索引が変わったときだけなので回数は少ない。実カタログでは未測定。
