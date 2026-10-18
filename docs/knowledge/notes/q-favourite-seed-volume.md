---
id: q-favourite-seed-volume
type: question
status: open
date: 2026-10-18
title: お気に入りの仮の好みの量が、掲載の公演の数・ツアーの会場の数・公演 ID の並び（先頭 60 件で切る）で変わる。お気に入り 1 件の証拠の量をどう決めるか（#108、測ってから）
sources:
  - https://github.com/island-6848/taguri-demo/issues/108
  - cloudflare/src/recommend.js
links:
  - depends_on: impl-favourite-seed
---
seedsFromFavourites は、名前を並べて先頭 20 件（MAX_SEED_FAVS）、ヒットした公演を ID の文字の順で先頭 60 件（MAX_SEED_STAGES）にする。personValues は公演ごとに人へ一定量を足すので、同じ人の公演が 1 件なら 0.554、10 件なら 1.205（issue の Node 実行）。
- 測ること: 同じお気に入りで、会場ごとの ID だけを増やす・ID を振り直す・名前を 21 件にしたときの、上位 15 件の入れ替わり
- 案: (1) ツアー（rec_stage.tour）を 1 件にまとめてから数える（〔fix-interest-tour-copies〕と同じ考え） (2) お気に入り 1 件あたりの合計を 1 に割る (3) 60 件の切り方を ID 順から「始まりの近い順」などに変える。どれも Python（build_recommend_index.seeds_from_favourites）と同じに直す必要がある
- 推し: (1) を先に（会場の数で好みが変わるのは明らかにおかしい）。(2) は FAV_SEED_W の強さとの兼ね合いがあるので測ってから
