---
id: q-answer-snapshot-shown
type: question
status: open
date: 2026-10-18
title: 答えたときの順位・点（answerSnapshot）は、その人の最新の控えの全国 400 件の中の位置で、画面に出していた順位・県・版とは限らない。表示したときの記録に答えを結び付けるか（#120、測る道具の直し）
sources:
  - https://github.com/island-6848/taguri-demo/issues/120
  - cloudflare/src/screens/evalrec.js
  - cloudflare/src/screens/recommend.js
links:
  - affects: impl-replay-eval
---
コードで確かめたこと（2026-10-18）: answerSnapshot は rec_cache の body.groups の中の位置を rank、b を score にする。県で絞った画面の 1 位が全国 100 位なら 100 が残る。別のタブで計算し直すと、答えた画面とは別の控えから取る。〔fix-api-recommend-delegates〕で /api/recommend が控えを上書きすることは無くなった（ずれの元の 1 つは消えた）。
- 案: 画面が答えと一緒に「出していた順位・県・版」を送り（web/app.js の変更が要る）、サーバーは控えの rank（モデルの順位）と並べて両方残す。保存は reaction の既存の列＋1〜2 列で、書き込みの回数は増えない
- 測ること: 本番の控えで、県で絞った画面の答えがどれだけあるか（rank のずれが効く範囲）
