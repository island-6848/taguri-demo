---
id: eval-favourite-seed
type: finding
status: confirmed
date: 2026-10-13
title: お気に入りを仮の評価にすると、評価0件のときだけ当たりが上がる（+0.014〜0.015）。すぐ薄めれば後で下がらない
sources:
  - docs/research/person-reco-eval.md
  - tools/review/eval_favourite_seed.py
links:
  - depends_on: lit-syskill-webert-prior
  - depends_on: dec-no-n1-evidence
  - affects: comp-recommender
---
公開の映画評価データ（選ぶ300人と確かめる500人は別、2抽出）。お気に入り（登録前の40件で2回以上すべて最高評価の人）の他の作品を、本人の上位5分の1（z = 0.4√12）の仮の評価として重み 3 /（3 + 本人の評価の数）で数え、お気に入り本人は外す。評価0件で +0.014 ±0.011、+0.015 ±0.010（良くなった人 56〜59%）、3件で +0.009／+0.003（区間は0をまたぐ）、10件以降は差なし。薄めない（重み1のまま）と40〜80件で −0.01 前後悪くなる。お気に入り本人を外すかどうかは差なし。お気に入りを本人の高評価から作っているため実際の申告より確かな可能性がある。舞台での効果は未確認。
