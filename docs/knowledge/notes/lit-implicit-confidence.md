---
id: lit-implicit-confidence
type: finding
status: confirmed
date: 2026-10-13
title: 観る前の反応（興味あり・購入）は「好みの信号」だが確からしさが違うので、重みを変えて扱う（Hu・Koren・Volinsky 2008）
sources:
  - https://andrewclark.super.site/all-media/collaborative-filtering-for-implicit-feedback-datasets
links:
  - supports: q-reco-learning-design
---
暗黙の反応を「好みの有無」と「その確からしさ」に分けて扱う。たぐりでは観劇後の評価を確かな信号、興味あり・購入・興味なしを確からしさの低い信号として扱う根拠になる。（論文の存在と要旨は出版元・著者のページで確かめた。本文はこの環境から読めず、検索結果の要約で見た範囲）
