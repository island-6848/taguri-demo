---
id: lit-popularity-bias
type: finding
status: unverified
date: 2026-10-15
title: 推薦は人気のあるものに偏りやすく、本人ごとに並べ直して少数派のものも混ぜる方法がある（Abdollahpouri・Burke・Mobasher, FLAIRS 2019）
sources:
  - https://ar5iv.arxiv.org/html/1901.07555
  - https://ceur-ws.org/Vol-2440/paper4.pdf
links:
  - affects: impl-person-ordinal-v3
---
Managing Popularity Bias in Recommender Systems with Personalized Re-ranking。人気の偏りを、精度をあまり落とさずに並べ直しで和らげる。同じ著者らは、人気の偏りが利用者の期待からのずれになると報告。たぐりでは、出演数の多い俳優ほど多くの公演に効くので、上位がその人の公演で埋まりやすい（作品ごと 1 枠にまとめる処理はあるが、人ごとの上限は無い）。要旨は検索結果の引用で見ただけ。
