---
id: impl-person-graded-v2
type: finding
status: confirmed
date: 2026-10-13
title: 推薦の計算を person-graded-v2 に変えた（Python 版と Worker 版の両方、同じ結果になることをテストで確認）
sources:
  - tools/review/user_recommender.py
  - cloudflare/src/recommend.js
  - cloudflare/test/recommend.test.js
links:
  - depends_on: dec-reco-graded
  - affects: comp-recommender
---
◎○△×＝4・3・2・1、その人の平均とばらつきで「いつもより高いか低いか」に直し、人物ごとに縮約した平均（Σz/(n+3)）、公演の点は上げる上位 3 人＋下げる上位 3 人。並びは点の順（v1 の「強い一致の数」の段は使わない）。Worker は浮動小数の計算順まで Python に合わせ、144 通りで一致、わざと壊すと落ちることを確認。結果の保存（rec_cache）は計算の名前を鍵に含める。挙動の変化: ×・×・△ の人には△の作品の人物が勧められるようになった（△は「まあ良いが気になる所がある」なので、その人の中では良いほう）。観点ごとの割り当ては入れていない。
