---
id: lit-ordinal-damping
type: finding
status: unverified
date: 2026-10-13
title: 評価を等間隔の数ではなく順序として扱う研究（OrdRec）と、少ない件数を割り引く「damping」は推薦の定番
sources:
  - https://recsys.acm.org/recsys11/session-methodological-issues/
  - https://lkpy.readthedocs.io/en/0.14.1/bias.html
  - https://evanmiller.org/bayesian-average-ratings.html
links:
  - affects: q-rating-scale
  - supports: eval-design-choices
---
Koren & Sill（RecSys 2011、OrdRec、最優秀論文）: 評価を数値ではなく順序として扱い、利用者ごとの区切りを学ぶ枠組み（区切りの作り方の細部は原文未確認）。LensKit の bias: 平均に「既定の評価を何件ぶん仮定するか」という damping を足して割る（たぐりの +3 と同じ形）。Bayesian average: 件数の少ないものを全体の平均に寄せる。どちらも「何件ぶん寄せるか」はデータで選ぶ値とされる。要旨・文書で見た範囲。
