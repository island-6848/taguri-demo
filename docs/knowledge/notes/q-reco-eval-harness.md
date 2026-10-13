---
id: q-reco-eval-harness
type: question
status: open
date: 2026-10-13
title: 推薦の改善を判断するための評価の仕組みをどう作るか（何のデータで・どの指標で）
links:
  - depends_on: q-real-catalog-stats
  - affects: comp-recommender
---
候補: 持ち主の EC2 の評価を時系列に分けて、今の計算（B0/B1）の NDCG@10 と学習曲線を出す（公開版の精度とは言わない）。公開版では提示→反応→観劇後の評価を結び付けて記録し始める。計算を変えるたびに Python と Worker の両方を直す負担もあるので、評価は索引（rec_*）の上で回せる形が望ましい。
