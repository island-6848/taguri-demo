---
id: lit-user-bias
type: finding
status: unverified
date: 2026-10-13
title: 推薦では、利用者ごとの評価の甘さ辛さ（user bias）を差し引いて扱うのが定番（Koren 2008 ほか）
sources:
  - https://www.bibsonomy.org/bibtex/6fde541c33e11d15f35cac9bc48b4cc1
  - https://ir.webis.de/anthology/1999.sigirconf_conference-99.31/
links:
  - affects: q-rating-scale
---
Koren（KDD 2008）の基準の予測は 全体の平均＋利用者の偏り＋作品の偏り。Herlocker ほか（SIGIR 1999）は協調フィルタリングの部品を比べた研究で、評価の正規化もその部品の一つとされる。どちらも式の細部は原文で確かめていない（二次資料・書誌情報のみ）。
