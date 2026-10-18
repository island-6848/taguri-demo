---
id: q-reco-time-decay
type: question
status: open
date: 2026-10-18
title: 好みの変化に古い評価が追いつけるか。personValues は昔の評価も同じ重さで数える（日付で減らさない）。全履歴・最近の窓・時間減衰を比べる（#117、測ってから）
sources:
  - https://github.com/island-6848/taguri-demo/issues/117
  - cloudflare/src/recommend.js
  - cloudflare/src/reco-gate.js
links:
  - depends_on: impl-person-ordinal-v3
---
- 測ること: 前半と後半で好みが変わる人工の系列で、新しい好みに追いつく速さ。好みが変わらない人・評価の少ない人が悪くならないか。時刻のある実データ（手元の再生）でも同じ比較
- 減衰を入れるなら Python と JS の両方（一致の試験）。時刻は rated_at（〔fix-rated-at〕）を使う。計算量はほぼ変わらない
