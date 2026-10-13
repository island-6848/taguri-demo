---
id: lit-mnar
type: finding
status: confirmed
date: 2026-10-13
title: 評価が付いていないこと自体が情報になり、付いた評価だけで学ぶ・測ると偏る（Steck 2010）
sources:
  - https://www.nokia.com/bell-labs/publications-and-media/publications/training-and-testing-of-recommender-systems-on-data-missing-not-at-random
links:
  - contradicts: q-reco-learning-design
---
Missing not at random。利用者は推薦されたものを観て評価しやすいので、付いた評価だけで測ると、今の推薦が勧めたものほど有利に見える。「反応しなかった公演は何とも扱わない」とした案は、この情報を捨てている。（論文の存在と要旨は出版元・著者のページで確かめた。本文はこの環境から読めず、検索結果の要約で見た範囲）
