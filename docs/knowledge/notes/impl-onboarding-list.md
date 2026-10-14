---
id: impl-onboarding-list
type: finding
status: confirmed
date: 2026-10-13
title: 最初の評価で聞く過去作の一覧を出す API を作った（お気に入りの公演 → 今後の候補を一番多く覆う公演）
sources:
  - cloudflare/scripts/build_recommend_index.py
  - cloudflare/src/worker.js
  - cloudflare/test/recommend.test.js
links:
  - answers: q-first-rating-onboarding
  - depends_on: eval-onboarding-selection
  - depends_on: impl-favourite-seed
  - affects: comp-recommender
---
索引を作るとき（`--today`、日本時間）に、もう始まった公演のうち、これから並ぶ公演の人物・種類タグ（重み＝その人・タグが出るこれからの公演の数）をまだ覆っていない分だけ一番多く足すものを順に 40 件選び、`rec_meta` の `onboarding` に版と一緒に入れる。`GET /migration-api/onboarding` は、お気に入り（人・原作者）が関わるもう始まった公演を先に、次にこの一覧を並べ、記録済みの公演を除いて最大 20 件を公開の項目だけで返す（`because` は favourite／catalogue）。版が違う一覧は使わない。候補は索引にある公演（これからと最近まで）だけなので、古い名作は出ない。最初の 1 回だけ見せる・「観ていない」で飛ばすのは画面側の仕事で、まだ作っていない（画面の移植と一緒に）。
