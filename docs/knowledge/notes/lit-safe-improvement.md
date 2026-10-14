---
id: lit-safe-improvement
type: finding
status: confirmed
date: 2026-10-13
title: 新しい方式は「前より悪くないと高い確信で言えるときだけ」採る、という考え方がある（Thomas ほか 2015）
sources:
  - https://proceedings.mlr.press/v37/thomas15.html
links:
  - supports: q-reco-learning-design
---
High confidence policy improvement（ICML 2015）。下限と信頼度を決め、悪い方式を返す確率を抑える。たぐりの「既定より当たるときだけ本人向けの重みを使う」は、点の比較ではなく、記録の少なさを考えた余裕を持たせるべきという根拠になる。（論文の存在と要旨は出版元・著者のページで確かめた。本文はこの環境から読めず、検索結果の要約で見た範囲）
