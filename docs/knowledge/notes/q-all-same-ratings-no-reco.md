---
id: q-all-same-ratings-no-reco
type: question
status: open
date: 2026-10-18
title: 評価がみな同じ段（全部 ◎ など）の利用者は、評価を何件足しても推薦が出ない（相対評価 person-ordinal-v3 の性質）。同点でも使える補助の道を作るか（#106、起案者の判断）
sources:
  - https://github.com/island-6848/taguri-demo/issues/106
  - cloudflare/src/recommend.js
links:
  - depends_on: impl-person-ordinal-v3
  - depends_on: reco-base-rate-relative
---
personValues の z は「本人の評価の中での位置」なので、同点ばかりだと z = 0 で誰の値も 0 になる（issue の例: A の別公演に 5/5 を 1 件・40 件、どちらも空）。画面のワンポイントは「◎ だけでなく ○△× も混ぜて」と書いているが、本心でない低評価を混ぜさせることになる。
- 案 1: 同じ段しか無い尺度では、その評価を仮の好み（お気に入りと同じ SEED_Z、重みは SEED_K/(SEED_K+件数)）として数える。評価が分かれた時点で相対評価に戻る
- 案 2: 同点が続くとき、画面で「この中で特によかったのは？」と 1 つ選んでもらう（比べる質問）
- 案 3: いまのまま、ワンポイントの説明だけ
- 推し: 案 1（計算が小さく、本人の入力だけで足りる）。人工の利用者で「全部 ◎ → 1 件 △ を足した」ときに順位が飛ばないかを測ってから。Python（user_recommender.person_values）と JS を同じに直す
