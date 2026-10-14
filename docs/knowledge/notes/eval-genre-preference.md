---
id: eval-genre-preference
type: finding
status: confirmed
date: 2026-10-13
title: 本人のジャンルの好みを足すと、人物だけより当たりが上がり、使うほどの伸びも大きくなる（映画の公開データ）
sources:
  - docs/research/reco-without-reputation.md
  - tools/review/eval_privacy_reco.py
links:
  - affects: comp-recommender
  - raises: q-theme-preference
---
docs/research/reco-without-reputation.md。graded＋本人のジャンル別「いつもより高い／低い」で、k=10 で +0.022〜0.028、k=80 で +0.034〜0.035（区間 ±0.006〜0.009）、k=80 で良くなった人 69〜74%。5→80 件の伸び 0.060〜0.066 → 0.076〜0.081。人物は再会するまで点が付かないが、ジャンルはほぼ全作品に付くため。観劇ではテーマ語・劇団などにあたる（未確認）。
