---
id: lit-hierarchical-user-model
type: finding
status: confirmed
date: 2026-10-13
title: 利用者ごとの好みを、全体の事前分布から少しずつ個人に寄せる学習は確立した方法（Zhang & Koren 2007）
sources:
  - https://www.ssrc.ucsc.edu/pub/zhang-sigir07.html
links:
  - supports: q-reco-learning-design
  - contradicts: dec-reco-per-user-eval
---
Bayesian hierarchical user modeling（SIGIR 2007）。利用者ごとの profile を、事前分布を共有しながら学ぶ。データが少ない人は事前に近く、多い人は個人に寄る。事前分布は普通は全利用者のデータから学ぶので、記録を集めない方針（dec-reco-per-user-eval）では、事前を「人が決めた既定の重み」にするしかない。（論文の存在と要旨は出版元・著者のページで確かめた。本文はこの環境から読めず、検索結果の要約で見た範囲）
