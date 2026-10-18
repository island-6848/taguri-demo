---
id: fix-api-recommend-delegates
type: decision
status: adopted
date: 2026-10-18
title: GET /api/recommend（/migration-api/recommend）は「今週のおすすめ」の画面と同じ計算・同じ控え（screens/recommend.rankedGroups）の全国上位 15 件をデータで返す。移行用の表（records・reactions）からの別の計算はやめた（#119）
sources:
  - https://github.com/island-6848/taguri-demo/issues/119
  - cloudflare/src/worker.js
  - cloudflare/src/screens/recommend.js
  - cloudflare/public/migration-data/recommend.js
  - cloudflare/scripts/measure_worker.mjs
  - cloudflare/test/recommend-screen.test.js
  - cloudflare/test/recommend.test.js
links:
  - affects: dec-reco-on-worker
  - raises: q-reco-screen-cpu-20-ratings
---
issue #119（2026-10-18）: 画面（/api/screen/recommend）は works・reaction・お気に入りから rankedGroups で計算するが、GET /api/recommend は移行用の records・reactions から recommendFor／computeRecommendations で別の計算をし、方式の版も person-ordinal-v3+fav3+asp1+tour1+why1 と screen-v22 で別だった。
- コードで確かめたこと: 2 つとも同じ rec_cache の行（user_id が主キー）に別の印で書くので、/api/recommend を開くたびに画面の控えが上書きされ、次の画面は計算し直しになっていた（無料枠の CPU を余分に使う）
- 決めたこと: 一本化する。recommendFor は screens/recommend.recommendApi を呼ぶだけにし、答えは画面の並び（filtered で都道府県なし、上位 TOP=15）・理由（人を先に、空きを種類で 3 つまで、使わなくなった種類は出さない）・会場（tours）・`recommender: screen-vNN|索引の版`・n_rated・n_linked・n_seeds。控えは画面と同じ行を読むだけ（読む行は rec_stage の表示用の列を出す分の会場だけ、最大で十数〜数十行）
- 試験: 画面の並びと同じ、控えを上書きしない（cached: true・印が同じ）、画面の答え（興味なし）がすぐ届く、移行用の /api/record は効かない。Python との一致は scoreFromIndex（144+24 通り）と collapseRanked（同じ全件）で確かめる。旧 API を通した一致の試験は外した
- 移行用の「アカウント・記録」の画面の文言も、今週のおすすめと同じものだと書き直した。CPU の測り（measure_worker.mjs）も works に入れて、この道を測るようにした
