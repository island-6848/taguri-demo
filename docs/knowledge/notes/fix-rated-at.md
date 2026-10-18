---
id: fix-rated-at
type: decision
status: adopted
date: 2026-10-18
title: 評価した順は works.rated_at（評価・詳細が変わったときだけ進む、migrations/0034）で決める。感想・日付などの編集で進む updated_at は使わない（無い行だけ代わりに使う）（#112）
sources:
  - https://github.com/island-6848/taguri-demo/issues/112
  - cloudflare/migrations/0034.sql
  - cloudflare/src/screens/rate.js
  - cloudflare/src/screens/diary.js
  - cloudflare/src/screens/recommend.js
  - cloudflare/src/recommend.js
  - tools/review/user_recommender.py
  - cloudflare/test/reco-gate.test.js
links:
  - affects: impl-hidden-gate
  - raises: q-replay-history-restore
---
issue #112（2026-10-18）: 感想の保存（/api/note）は評価と同じ works.updated_at を進め、ratedWorks はそれを評価の時間順として裏の答え合わせ（chooseVariant）に渡していた。issue の例（試験の人工利用者 user(60,'dir',2) の 10 件目の updated_at だけを後日に）で base → author_strong に変わった。
- 直したこと: works に rated_at を足し（migrations/0034。いまある評価は updated_at から始める。書き込みは評価のある行数だけ 1 回）、/api/rate で評価が変わったとき・詳細（aspects）が変わったときだけ進める。同じ評価を押し直しても進めない。記録をまとめる（merge）で評価を移すときは時刻も移す
- 順の決め方（recommend.ratedTime・user_recommender.independent_ratings、JS と Python で同じ）: rated_at → updated_at → 観劇日。rated_at の無い行（移行より前に書いた行、旧 API の records）は前と同じ
- 画面の控えは screen-v26
- 残り: 評価を直した記録は、直した時刻の 1 つだけが残る（直す前の評価・時刻の履歴は無い）。issue の「時間順評価では当時の評価版を使う」は履歴が要るので、手元の再生（〔q-replay-history-restore〕、#113）と一緒に考える
