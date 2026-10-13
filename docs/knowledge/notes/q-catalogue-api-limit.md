---
id: q-catalogue-api-limit
type: question
status: open
date: 2026-10-13
title: Worker の /api/catalogue は 1,000 件までしか返さない。これからの公演がそれより多いときどうするか
sources:
  - cloudflare/src/worker.js
links:
  - depends_on: dec-d1-catalogue-delivery
  - depends_on: q-real-catalog-stats
---
いまの本番 Worker は開始日が 30 日前以降の公演を、日付順に 1,000 件までしか返さない（LIMIT 1000）。サイトマップで 6,000 件を読んだ初回は、これからの公演が 1,000 件を超えるかもしれず、超えた先の日付の公演が画面に出ない。
初回の取得で件数を数えてから、ページ分け・地域での絞り込みなど、画面の作り（移行中の画面）に合わせて決める。

追記（2026-10-13）: サイトマップ版の初回で、これから／上演中の公演は 1,353 件だった（sitemap-first-run）。1,000 件の上限は実際に足りない。
