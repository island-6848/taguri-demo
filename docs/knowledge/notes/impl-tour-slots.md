---
id: impl-tour-slots
type: finding
status: confirmed
date: 2026-10-14
title: Worker の推薦でもツアー公演を 1 枠にまとめ、ほかの会場を付けて出すようにした（+tour1）
sources:
  - tools/review/user_recommender.py
  - cloudflare/scripts/build_recommend_index.py
  - cloudflare/src/recommend.js
  - cloudflare/src/worker.js
  - cloudflare/migrations/0016.sql
links:
  - affects: comp-recommender
---
同じツアーの判定は Python の画面（collapse_tours）と同じ「題名・団体（正規化）・クレジット」。クレジットは並び順でなく集合で比べるように Python 側も直した（会場ごとのページでクレジットの並びが違うと別の公演と扱われていた）。索引を作るときに公演ごとのツアー鍵（tour_key、16 桁）を rec_stage.tour に入れ、Worker は点を付けた公演の期間を読むのと同じ問い合わせで鍵も読む（読む行は増えない）。反応した公演を外したあとで、点の一番高い会場を代表にし、ほかの会場を点の順に tours に付けて上位 15 枠を出す。架空のカタログ（会場違いのツアー、クレジットの並び違いを含む）で、Python の collapse_tours と同じまとまりになることをテストで確認した。索引を作り直すまで rec_stage.tour は空で、そのあいだは 1 会場 1 枠のまま。
