---
id: comp-native-screens
type: component
status: planned
date: 2026-10-13
title: 元の画面の Worker 版（cloudflare/src/screens/）
sources:
  - https://github.com/island-6848/taguri-demo/blob/cloudflare-d1-preview/cloudflare/src/screens/index.js
  - https://github.com/island-6848/taguri-demo/blob/cloudflare-d1-preview/docs/render-migration-plan.md
links:
  - affects: comp-public-server
  - affects: comp-frontend
---
Python が組んでいた /api/screen/* と POST /api/* を JS に移したもの。NATIVE_UI で有効にした分だけ Worker が答える（本番は未設定）。Python と同じ手順を流して同じ応答になることを test/screens.test.js が確かめる。
