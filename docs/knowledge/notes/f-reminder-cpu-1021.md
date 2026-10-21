---
id: f-reminder-cpu-1021
type: finding
status: confirmed
date: 2026-10-21
title: 開幕リマインドは 1 回 Worker の CPU 30〜40 ミリ秒（無料は 10 ミリ秒）で、「いまは一時的に止めています」（503）の見込みの原因。週の束の使い回し・中身を開いたときに読む・entry を D1 で取り出す、で 10〜12 ミリ秒にした
sources:
  - cloudflare/src/screens/reminder.js
  - cloudflare/src/screens/index.js
  - cloudflare/src/worker.js
  - web/app.js
links:
  - depends_on: workers-free-cpu-10ms
  - affects: d1-reads-over-1020
---
起案者の画面に「いまは一時的に止めています。少し時間をおいてから、もう一度試してください。」が出た（2026-10-21）。

- **出る条件:** 画面の取得が 503 で、答えに文が無いとき（app.js の failWords）。たぐりの 503 はどれも文を付けて返す。文が無いのは Cloudflare が返した 503 と見込んだ。無料の Worker は 1 回 CPU 10 ミリ秒まで〔workers-free-cpu-10ms〕で、越えると Cloudflare が止める（Error 1102、503）。本番のログは見ていない（この作業環境から見られない）
- **測り方:** 本番の大きさの索引（rec_stage 5,099 行など）と、記録 40 件・興味あり 15 件の利用者 1 人。worker.fetch の時間から D1 の待ちを引いた（scratchpad の cpu2.mjs）。この機械と Cloudflare では速さが違うので、目安にとどまる
- **画面ごと（直す前）:** 開幕リマインド 30〜40 ミリ秒（答え 253 KB）、探す 10〜20、眺める・興味ありの 1 回目 12〜15、おすすめの計算し直し 70（記録が変わった直後の 1 回だけ）。ほかは 5 ミリ秒以下
- **開幕リマインドで直したこと:**
  1. 同じ週の束（weekAll）を最大 4 回組んでいたのを 1 回にした
  2. 行を開いたときの中身（日程・出演・あらすじ・料金）は、開いたときに /api/reminder_detail で読む。前は 1 週ぶん（約 170 件）を毎回組んでいた。開くと「読み込んでいます…」が一瞬出る
  3. rec_stage の entry・catalogue の metadata は丸ごと JSON.parse せず、使う欄だけを D1 の json_extract で取り出す。D1 の中の手間は Worker の CPU に数えない
  4. ポスターは出す行の分だけ読む
  5. 画面の答えに TOKEN を入れるのに、答え全体を JSON にして戻していた（どの画面でも）。文字列だけを差し替える形にした
- **直した後:** 開幕リマインド 10〜12 ミリ秒（答え 168 KB）。残りの大半は約 170 行の HTML を組む分で、まだ 10 ミリ秒の境目にいる。次に減らすなら、日ごとの束を開いたときに読む形
- **残り:** おすすめの計算し直し（70 ミリ秒）は recommend.js（もう一つのセッションの受け持ち）なので知らせた。探す（10〜20）は issue #242 の読み出しと合わせて直す
