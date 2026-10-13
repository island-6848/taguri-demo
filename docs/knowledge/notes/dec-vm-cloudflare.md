---
id: dec-vm-cloudflare
type: decision
status: superseded
date: 2026-10-13
title: サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く
sources:
  - docs/service-roadmap.md
links:
  - supersedes: dec-render-service-beta
  - depends_on: dec-own-domain
  - affects: comp-public-server
  - affects: comp-auth-throttle
  - affects: comp-vm-host
verifies:
  - S02
  - S13
  - S22
---
今の Python のコードをほぼそのまま動かせ、ディスクも消えない。Cloudflare Tunnel で HTTPS 化し、ポートを開けない。必要な費用はドメイン代だけを目指す。
（2026-10-13、起案者が Workers＋D1 に寄せると決めた）置き換え済み。
