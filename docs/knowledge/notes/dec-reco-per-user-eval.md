---
id: dec-reco-per-user-eval
type: decision
status: adopted
date: 2026-10-13
title: 推薦の改善は、利用者ごとに「その人にとって良くなったか」だけを確かめる（記録を集めない）
links:
  - affects: q-reco-eval-harness
  - affects: dec-reco-measure-first
  - affects: comp-recommender
  - raises: q-reco-personal-backtest
---
起案者の指示（「記録を集めると、プライバシーにかかわる。あくまで多数の参加者から効果を検証するのではなく、そのユーザーにとって向上したかだけわかればよい」）。利用者をまたいだ集計・提示ログの収集・A/B はしない。確かめるのは、その人の記録の中だけで、結果もその人にだけ見せる。
