---
id: impl-rating-aspects
type: finding
status: confirmed
date: 2026-10-13
title: 「気になった所」を記録に付けられるようにし、低い評価を観点に応じた役職に効かせるようにした（+asp1）
sources:
  - tools/review/user_recommender.py
  - cloudflare/src/recommend.js
  - cloudflare/src/reco-gate.js
  - cloudflare/migrations/0012.sql
  - tools/review/rate_performances.py
links:
  - answers: q-rating-aspects
  - depends_on: stage-roles
  - depends_on: rating-mixes-aspects
  - depends_on: impl-hidden-gate
  - affects: comp-recommender
---
観点は 8 つ（話・脚本・構成／演出・見せ方／演技・出演／歌・音楽／ダンス／美術・衣裳／値段に見合わない／会場・座席）。本人の真ん中より低い評価（順位の値が負）だけ、関わった人への効き方を観点ごとの割合（主に 1.0・少し 0.5・ほんの少し 0.2、表にない役職は 0）で変える。演技の不満は演出家に 0.2（起案者の指示）。値段は料金欄の一番高い額から #値段 の帯タグ（4 段）を作り、そこだけに効かせる（作り手を下げない）。会場は #会場 だけ。保存は D1 の records.aspects・works.aspects（0012）と Render の works.aspects、Worker の /api/record が受ける。Python（参照実装・Render の推薦）と Worker が同じ点を出すことを一致テストで確かめた。裏の答え合わせに「使わない」版を加え、本人の記録で使わないほうがはっきり当たる人だけ切り替える。入力のボタン（評価の画面）は画面の移植と一緒に作る（未）。割合は仮の値で、人ごとに学ぶ形はまだ入れていない。
