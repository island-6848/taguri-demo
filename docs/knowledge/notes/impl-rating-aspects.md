---
id: impl-rating-aspects
type: finding
status: confirmed
date: 2026-10-13
title: 評価の詳細（項目ごとの良かった／気になった）を記録に付けられるようにし、評価を項目に応じた役職に効かせるようにした（+asp1）
sources:
  - tools/review/user_recommender.py
  - cloudflare/src/recommend.js
  - cloudflare/src/reco-gate.js
  - cloudflare/migrations/0015.sql
  - tools/review/rate_performances.py
links:
  - answers: q-rating-aspects
  - depends_on: dec-rating-detail-mode
  - depends_on: stage-roles
  - depends_on: rating-mixes-aspects
  - depends_on: impl-hidden-gate
  - affects: comp-recommender
---
観点は 8 つ（話・脚本・構成／演出・見せ方／演技・出演／歌・音楽／ダンス／美術・衣裳／値段に見合わない／会場・座席）。本人の真ん中より低い評価（順位の値が負）だけ、関わった人への効き方を観点ごとの割合（主に 1.0・少し 0.5・ほんの少し 0.2、表にない役職は 0）で変える。演技の不満は演出家に 0.2（起案者の指示）。値段は料金欄の一番高い額から #値段 の帯タグ（4 段）を作り、そこだけに効かせる（作り手を下げない）。会場は #会場 だけ。保存は D1 の records.aspects・works.aspects（0015）と Render の works.aspects、Worker の /api/record が受ける。Python（参照実装・Render の推薦）と Worker が同じ点を出すことを一致テストで確かめた。裏の答え合わせに「使わない」版を加え、本人の記録で使わないほうがはっきり当たる人だけ切り替える。入力のボタン（評価の画面）は画面の移植と一緒に作る（未）。割合は仮の値で、人ごとに学ぶ形はまだ入れていない。

2026-10-14 追記: 「良かった」も付けられるようにした（コードの先頭に +）。高い評価は良かった項目の役職に、低い評価は気になった項目の役職に主に効き、反対側の項目が指す役職にはその分（1 − 割合）だけ弱く効く。符号は変えない（低い評価で良かった人を上げることはしない）。項目「値段に見合わない」は「値段」に改名。作ったデータ（出演と話が別々に効く利用者が、良い側に +、悪い側に印を付ける）で、使わない版は区切りで 192 勝 288 敗（評価 60 件、100 人）、切り替わった人 0（cloudflare/test/reco-gate.test.js）。

2026-10-18 追記: 詳細を 5 段階（"--code"〜"++code"）と「この作品には無い」（"~code"）にした〔dec-aspects-five-levels〕。項目の効き方はその記録で最も強い印に対する強さで割り引く。強さがそろった記録（3 段階の記録すべて）は前と同じ点。無い項目は推薦に使わない。
