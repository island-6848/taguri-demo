---
id: comp-vm-host
type: component
status: planned
date: 2026-10-13
title: サービス版の VM（cloudflared・systemd）
sources:
  - docs/service-roadmap.md
links:
  - depends_on: q-vm-host-choice
---
サービス版を常時動かす VM。外へはポートを開けず、cloudflared が Cloudflare へ外向きにつなぐ。サーバーは 127.0.0.1 で待ち受ける。
