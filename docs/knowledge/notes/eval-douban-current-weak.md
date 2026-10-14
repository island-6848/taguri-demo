---
id: eval-douban-current-weak
type: finding
status: confirmed
date: 2026-10-13
title: 公開の映画評価データ（実在の 500 人）では、今の推薦は当てずっぽうに近い（AUC 0.50〜0.53）
sources:
  - docs/research/person-reco-eval.md
  - tools/review/eval_person_reco.py
  - https://raw.githubusercontent.com/librahu/HIN-Datasets-for-Recommendation-and-Network-Embedding/master/README.md
links:
  - affects: comp-recommender
  - answers: q-reco-learning-design
---
docs/research/person-reco-eval.md。最初の k 件だけでその人の残りの評価を当てる比較で、今の計算（person-feedback-v1 と同じ式）は k=5〜80 で 0.504〜0.533。点を付けられる映画が少なく（k=40 で 12%）、付けた点の当たりも弱い。映画のデータで、評価の日時が無い点に注意。
