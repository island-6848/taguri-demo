---
id: render-two-identities
type: finding
status: confirmed
date: 2026-10-13
title: Render の利用者（tg_session）とログインしたアカウント（D1）は別人として扱われている
sources:
  - https://github.com/island-6848/taguri-demo/blob/cloudflare-d1-preview/cloudflare/src/original-ui.js
links:
  - raises: q-direction
  - supports: dec-render-full-migration
---
元の画面で付けた「興味あり」やお気に入りは、別の端末でログインし直しても出てこない。「アカウント・記録」の画面で入れた分だけがアカウントに付いてくる。
