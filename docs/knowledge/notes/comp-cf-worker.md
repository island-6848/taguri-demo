---
id: comp-cf-worker
type: component
status: current
date: 2026-10-13
title: Cloudflare Worker（cloudflare/src/worker.js）
sources:
  - https://github.com/island-6848/taguri-demo/blob/cloudflare-d1-preview/cloudflare/src/worker.js
  - https://github.com/island-6848/taguri-demo/blob/cloudflare-d1-preview/cloudflare/wrangler.jsonc
  - https://github.com/island-6848/taguri-demo/pull/5
---
cloudflare-d1-preview ブランチ。D1・静的ファイル・ログイン・推薦・元の画面への中継（ORIGINAL_UI_BRIDGE）を受け持つ。push するたびに Workers Builds が D1 の migration を当ててから deploy する。
