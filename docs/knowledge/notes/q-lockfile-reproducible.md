---
id: q-lockfile-reproducible
type: question
status: open
date: 2026-10-13
title: Worker の依存とログイン画面の組み立てを再現できるようにするか（lockfile）
sources:
  - https://github.com/island-6848/taguri-demo/blob/cloudflare-d1-preview/docs/cloudflare-security-review.md
links:
  - affects: comp-cf-worker
---
セキュリティ点検の S4。package-lock.json を入れておらず、同梱した public/vendor/*.js がソースから同じものになるかを確かめていない。
