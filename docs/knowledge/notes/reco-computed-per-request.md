---
id: reco-computed-per-request
type: finding
status: confirmed
date: 2026-10-12
title: おすすめは開くたびに全候補を計算している
sources:
  - docs/user-recommendation-loop.md
links:
  - supports: dec-defer-workers
  - affects: comp-recommender
  - answers: q-workers-free-viable
verifies:
  - S20
---
推薦ジョブとプロフィールのキャッシュは入れていない。CPU 10 ミリ秒の制限には収まらない作りである。
