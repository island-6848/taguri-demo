---
id: workers-cache-api-workers-dev
type: finding
status: confirmed
date: 2026-10-13
title: Workers の Cache API は *.workers.dev では何もしない（独自ドメインでだけ効く）
sources:
  - https://developers.cloudflare.com/workers/runtime-apis/cache/
  - https://community.cloudflare.com/t/cloudflare-worker-cache-does-not-work/298125
links:
  - affects: dec-free-tier-only
---
公式の説明（検索結果の引用で確かめた）に「*.workers.dev での Cache API の操作は効かない」とある。サービス版は workers.dev の URL なので、R2 のポスターを Worker の cache で受け止めることはできない。読み出し（Class B）を減らすのは、ブラウザの cache（`Cache-Control: private, max-age=604800, immutable`）に任せる。独自ドメインは費用がかかるので使わない。
