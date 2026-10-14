---
id: eval-douban-graded-better
type: finding
status: confirmed
date: 2026-10-13
title: 全部の段階をその人基準（いつもより高いか低いか）で使うと、62〜82% の人で今の推薦より良く、使うほど差が広がる
sources:
  - docs/research/person-reco-eval.md
links:
  - supports: q-rating-scale
  - supports: lit-decoupled-rating
  - supports: lit-negative-ratings
  - affects: comp-recommender
---
docs/research/person-reco-eval.md。graded は k=5〜80 で 0.510〜0.572（今の計算は 0.504〜0.533、95% 区間 ±0.003〜0.005）。良くなった人の割合は k=5 で 62〜64%、k=80 で 79〜82%（2 通りの抽出）。辛口・中くらい・甘口のどの人でも良くなった。低い評価を使わない版は今の計算と同じか少し悪く、低い評価を使うことが効いている。
