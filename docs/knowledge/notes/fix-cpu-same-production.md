---
id: fix-cpu-same-production
type: finding
status: unverified
date: 2026-10-18
title: 「読み込めませんでした SyntaxError: Unexpected token '<'」── 同じ公演をまとめる処理が作り手の一覧を全部読んで、Worker の CPU 10 ミリ秒を越えたと見る
sources:
  - cloudflare/src/screens/recommend.js
  - cloudflare/src/screens/rate.js
  - web/app.js
  - docs/free-tier-budget.md
links:
  - depends_on: dec-ui-1018b
---
起案者の報告（2026-10-18）「読み込めませんでした　SyntaxError: Unexpected token '<', "<!DOCTYPE "... is not valid JSON が出る」。
- 意味: 画面の API が JSON ではなく HTML（Cloudflare のエラーのページ）を返した。Worker が途中で止まったときの形
- 見立て（本番のログは見られないので unverified）: その日の朝に入れた sameProduction（v19・v20）が、残す候補と答えた公演の 900 件前後の作り手の一覧（credits。1 件 40 人ほど）を読んで JSON を解いていた。手元の試し（1,300 件・作り手 40 人・答えた 300 件、SQLite の時間を除く）で、この関数だけで 9〜16 ミリ秒。無料枠の 1 回 10 ミリ秒（〔workers-free-cpu-10ms〕）を越える。版を上げたので誰でも最初の 1 回は計算し直しになり、そこで止まると控え（rec_cache）が書かれず、毎回止まる
- 直したこと: まず題名・団体・会場の短い列だけを読み、作り手は「題名が同じで、団体も会場も決め手にならない組」だけあとで読む。会場名の表記ゆれ寄せ（NFKC）も同じ題名が 2 つ以上ある組だけ。試しで 5 ミリ秒前後（そのうち JS の仕事は 0.5 ミリ秒ほどで、残りは結果の受け取り）。版 screen-v21
- 同じ心配のある所: 未評価は全件を 1 枚に出すので、作り手・あらすじを添えるのは先頭の 40 件まで
- 画面: JSON でない返事は「サーバーの処理が途中で止まりました（状態の番号）。少し待ってから、ページを読み込み直してください。」と出す。先に飛ばした読み込みが失敗したら 1 回だけ取り直す
- 分からないこと: 本番で実際にどの画面が止まったか、本当に CPU の上限か（Cloudflare のダッシュボードの Workers のログ・エラーの数で確かめられる）。measure_worker.mjs（本物の索引で測る）は取得の環境で走らせる
