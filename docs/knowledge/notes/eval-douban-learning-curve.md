---
id: eval-douban-learning-curve
type: finding
status: confirmed
date: 2026-10-13
title: 答え合わせの問題を固定しても、使うほど当たりは上がる（今の計算で 63%、graded で 74% の人）。ただし水準は低い
sources:
  - docs/research/person-reco-eval.md
links:
  - supports: dec-reco-graded
  - raises: q-public-reputation-signal
---
docs/research/person-reco-eval.md。各人の最後の 40 件を固定し、使える記録を 5→80 件に増やした（439 人）。AUC は今の計算 0.507→0.537、graded 0.511→0.571。上がった人は 63% と 74%、平均の上がり幅は 0.030 と 0.060。80 件でも 0.57 なので、「使うほど上がる」は成り立つが、当たりの水準を上げるには別の手がかりが要る。映画のデータで、評価の日時が無い。
