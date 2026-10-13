---
id: q-reco-eval-harness
type: question
status: open
date: 2026-10-13
title: 推薦の改善を判断するための評価の仕組みをどう作るか（何のデータで・どの指標で）
links:
  - depends_on: dec-reco-per-user-eval
  - depends_on: dec-no-n1-evidence
  - depends_on: q-real-catalog-stats
  - affects: comp-recommender
---
持ち主 1 人の評価で測る案は、n=1 なので採らない（dec-no-n1-evidence）。多数の利用者の記録を集めて比べる案は、プライバシーの理由で採らない（dec-reco-per-user-eval）。その人の記録だけで、その人にとって良くなったかを確かめる（q-reco-personal-backtest）。計算を変えるたびに Python と Worker の両方を直す負担もあるので、評価は索引（rec_*）の上で回せる形が望ましい。
