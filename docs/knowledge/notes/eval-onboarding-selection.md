---
id: eval-onboarding-selection
type: finding
status: confirmed
date: 2026-10-13
title: 最初に評価してもらう過去作を、これから並べる候補に多い人物・ジャンルから選ぶと、同じ件数で当たりが上がる（楽観的な条件）
sources:
  - docs/research/reco-without-reputation.md
  - https://files.grouplens.org/papers/voi-final.pdf
links:
  - affects: comp-recommender
---
docs/research/reco-without-reputation.md（eval_elicitation.py）。graded で k=5〜40 に +0.033〜0.060（区間 ±0.007〜0.011）、カタログ全体で多いもの基準だと +0.004〜0.010。候補が本人の評価済み 40 件なので実際より有利。Rashid ほか（2002）と同じ方向。
