---
id: eval-design-choices
type: finding
status: confirmed
date: 2026-10-13
title: 推薦の計算の細部（数字への直し方・平均か合計か・割り引き・足す人数）はほぼ差が無く、効くのはジャンルの好みと監督の重みを上げること
sources:
  - docs/research/person-reco-eval.md
  - tools/review/eval_design_choices.py
links:
  - affects: comp-recommender
  - supports: eval-genre-preference
---
公開の映画評価（選ぶ 300 人・確かめる 500 人、2 通りの抽出、物差し 2 つ）。等間隔の 4・3・2・1 とその人の中の順位はほぼ同じ。平均と合計は同じ。割り引きの強さ（0〜10）はほぼ差なし（映画では同じ人に再会しにくい）。足す人数は 3・5・全員が同じで 1 だけ少し悪い（映画は出演者が少なく、舞台の大人数の公演では未確認）。監督の重みは 1.0 が 0.4 よりわずかに良い。本人のジャンルの好みを重み 1〜2 で足すとはっきり上がる。「最高評価だけ」に直す方法は最高評価の当たりだけ上がり、△と×の順は悪くなる。
