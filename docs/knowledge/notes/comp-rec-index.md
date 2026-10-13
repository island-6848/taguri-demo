---
id: comp-rec-index
type: component
status: current
date: 2026-10-13
title: 推薦の索引の作成（build_recommend_index.py）
sources:
  - https://github.com/island-6848/taguri-demo/blob/cloudflare-d1-preview/cloudflare/scripts/build_recommend_index.py
links:
  - depends_on: comp-catalog-pipeline
  - affects: comp-recommender
---
EC2 のカタログから rec_stage・rec_credit・rec_people・rec_gram を作り、版を切り替えて入れる SQL を出す。--stats で件数と書き込み行数を出す。
