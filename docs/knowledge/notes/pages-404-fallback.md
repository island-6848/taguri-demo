---
id: pages-404-fallback
type: finding
status: confirmed
date: 2026-10-12
title: GitHub Pages は知らない道に 404.html を返し、画面はそれで深い道を開いている
sources:
  - web/404.html
  - web/index.html
links:
  - affects: comp-frontend
verifies:
  - S09
---
`/taguri-demo/app/calendar` のような道も 404.html（index.html と同じ中身）で開く。応答の状態は 404 になる。
