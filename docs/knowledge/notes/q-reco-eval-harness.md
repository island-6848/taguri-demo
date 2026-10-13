---
id: q-reco-eval-harness
type: question
status: open
date: 2026-10-13
title: 推薦の改善を判断するための評価の仕組みをどう作るか（何のデータで・どの指標で）
links:
  - depends_on: dec-no-n1-evidence
  - depends_on: q-real-catalog-stats
  - affects: comp-recommender
---
持ち主 1 人の評価で測る案は、n=1 なので採らない（dec-no-n1-evidence）。複数の利用者のデータが要る: 公開版で、見せた推薦→反応（興味あり・興味なし・購入）→観劇後の評価を結び付けて記録し始め、集まってから比べる。計算を変えるたびに Python と Worker の両方を直す負担もあるので、評価は索引（rec_*）の上で回せる形が望ましい。
