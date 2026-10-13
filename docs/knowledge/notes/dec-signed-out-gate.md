---
id: dec-signed-out-gate
type: decision
status: adopted
date: 2026-10-13
title: ログインしていない人に見せるのは「ログイン」と「たぐりとは」だけ
sources:
  - https://github.com/island-6848/taguri-demo/blob/cloudflare-d1-preview/cloudflare/src/worker.js
  - https://github.com/island-6848/taguri-demo/blob/cloudflare-d1-preview/cloudflare/test/gate.test.js
links:
  - affects: comp-cf-worker
---
起案者の指示。/ は /about へ、ほかのページは /login?next= へ送る。データの API と画像は 401。戻り先は同じサイトの中だけ（safeNext）。
