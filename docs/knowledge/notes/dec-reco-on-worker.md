---
id: dec-reco-on-worker
type: decision
status: adopted
date: 2026-10-13
title: おすすめ（人物得点）は索引をバッチで作り、Worker で計算する
sources:
  - https://github.com/island-6848/taguri-demo/blob/cloudflare-d1-preview/cloudflare/src/recommend.js
links:
  - supersedes: reco-computed-per-request
  - depends_on: reco-js-parity
  - affects: comp-recommender
---
段1で利用者によらない部分（rec_*）を作り、段2で Worker が◎の人の行だけ読んで計算する。結果は rec_cache に保存し、記録・反応・日付・版が変わったときだけ計算し直す。
