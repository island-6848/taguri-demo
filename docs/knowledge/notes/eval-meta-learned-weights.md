---
id: eval-meta-learned-weights
type: finding
status: confirmed
date: 2026-10-13
title: 組み合わせの重みを公開データの別の人で学んで固定すると少し上がる（+0.006）。人ごとに学び直すのと小さな MLP は効かない
sources:
  - docs/research/reco-without-reputation.md
links:
  - supports: lit-hierarchical-user-model
  - affects: comp-recommender
---
docs/research/reco-without-reputation.md。人物＋ジャンルの重みを評価対象と重ならない公開データの 1,000 人でリッジ回帰（記録数との掛け合わせ項つき）。k=80 で 0.611〜0.618。学んだ重みは出演・監督ほぼ同じ、ジャンルは記録が増えるほど重く。人ごとに学び直して既定値に寄せる方法は「ほぼ寄せない」が選ばれ、自由に学ぶと悪化し伸びも消えた。隠れ層 32 の MLP は線形と同じ。
