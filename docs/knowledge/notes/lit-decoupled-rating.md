---
id: lit-decoupled-rating
type: finding
status: confirmed
date: 2026-10-13
title: 「好み」と「評価の付け方の癖」を分けて扱うと精度が上がり、順位だけを使うと情報を捨てすぎる（Jin・Si・Zhai 2003）
sources:
  - https://timan.cs.illinois.edu/czhai/pub/uai2003-cf.pdf
  - https://mlanthology.org/uai/2003/jin2003uai-preference
links:
  - supports: q-rating-scale
  - contradicts: reco-base-rate-relative
---
Preference-based Graphic Models for Collaborative Filtering（UAI 2003）。好みが似ていても評価の付け方は人によって大きく違う（何でも高く付ける人がいる）ことを問題にし、好みと評価を別の変数に分けた decoupled model が 5 つの既存手法より有意に良かった。一方、作品の順位だけを使う preference model はかなり悪かった ― 評価の値の情報を全部捨てるべきではない。2 つの映画評価データでの結果。著者の PDF と書誌で確かめた（本文の数値は未確認）。
