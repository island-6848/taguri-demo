---
id: reco-js-parity
type: finding
status: confirmed
date: 2026-10-13
title: Worker の推薦は Python（person-feedback-v1）と同じ結果を出す
sources:
  - https://github.com/island-6848/taguri-demo/blob/cloudflare-d1-preview/cloudflare/test/recommend.test.js
  - https://github.com/island-6848/taguri-demo/blob/cloudflare-d1-preview/cloudflare/test/test_recommend_index.py
links:
  - affects: comp-recommender
---
架空カタログ 12×履歴 4×重み 3 の 144 通りで、公演・順位・点数・理由が一致する。計算をわざと壊すとテストが落ちる。足し算の順番・6 桁の丸め・文字列のコードポイント順を Python に合わせた。
