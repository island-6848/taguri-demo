---
id: lit-multi-criteria
type: finding
status: confirmed
date: 2026-10-13
title: 総合評価に加えて観点ごとの評価を使う推薦（多基準推薦）は、1 つの評価だけより精度が上がったと報告されている（Adomavicius & Kwon 2007 ほか）
sources:
  - https://web-ainf.aau.at/pub/jannach/files/Conference_ACMEC2012.pdf
  - https://www.springerprofessional.de/en/multi-criteria-recommender-systems/1519568
  - https://ir.webis.de/anthology/2014.sigirconf_conference-2014.10
links:
  - supports: q-rating-aspects
---
Adomavicius & Kwon（IEEE Intelligent Systems 2007）は、観点ごとの評価を推薦に入れる 2 つのやり方を示し、映画で 1 つの評価の近傍法より精度が上がった（後続の Jannach ほかの論文の紹介による）。Recommender Systems Handbook に多基準推薦の章がある。Zhang ほか（SIGIR 2014, EFM）は、レビューの文から観点と好き嫌いを取り出し、観点ごとの好みで推薦と説明を行った。どれも書誌・要旨・二次資料で確かめた範囲。
