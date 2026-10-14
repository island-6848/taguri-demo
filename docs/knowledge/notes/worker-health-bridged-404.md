---
id: worker-health-bridged-404
type: finding
status: confirmed
date: 2026-10-13
title: 本番の Worker の /api/health は、Render への橋渡しに取られて 404 になっていた（直した）
sources:
  - cloudflare/src/worker.js
  - cloudflare/src/original-ui.js
  - cloudflare/test/posters.test.js
links:
  - affects: catalog-age-check
  - supports: dec-free-tier-only
---
本番は ORIGINAL_UI_BRIDGE=true で、`isOriginalRoute` が `/api/` のほとんどを Render へ渡す。`/api/health` は Render 側の許す一覧に無いので 404（「この操作は見つかりませんでした」）が返っていた。試験の環境で確かめた。カタログの日付の見張り（catalog-age.yml）も、無料枠の数え（free_tier）もこれを見るので、橋渡しより先に Worker が答えるようにした。
