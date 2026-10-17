---
id: lit-percentile-transform
type: finding
status: confirmed
date: 2026-10-17
title: 評価を利用者ごとの百分位に直してから推薦すると、ランキングの精度が上がった（Mansoury・Burke・Mobasher, ACM TIST 2021）。たぐりの順序化（式 1–2）とほぼ同じ考え方
sources:
  - https://dblp.org/pid/58/2337
  - https://vivo-cub.colorado.edu/display/pubid_308948
links:
  - supports: impl-person-ordinal-v3
  - affects: q-academic-novelty
---
M. Mansoury, R. Burke, B. Mobasher. Flatter Is Better: Percentile Transformations for Recommender Systems. ACM Transactions on Intelligent Systems and Technology 12(2): 19:1–19:16, 2021（arXiv 1907.07766, 2019）。書誌は dblp と CU Boulder の記録で確かめた。

- 中身（検索結果の要約）: 平均を引く・z 値にするのは分布の中心しか直さず、形（偏り）は直さない。評価を利用者ごとの百分位に直す前処理で、4 つの実データでランキングの精度が上がった。例として、同じ 4 点が Alice では百分位 80、Bob では 50 になる。
- たぐりとの関係: 式 1 の F_u（下の数＋同じ数の半分を総数で割る）は、同順位を中央で扱う百分位そのもの。式 2 はそれを ½ だけずらして √12 を掛けた形。つまり式 1–2 には直接の先行研究がある。違いは、段階数 L ごとに分けて数えること（星と ◎○△× を混ぜる人への対応）と、√12 で一様分布のばらつきを 1 にそろえることだけ。
- 本文は読めていない（arxiv.org はこの環境から開けない）。同順位の扱い（mid-rank か）は未確認。
