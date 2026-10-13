---
id: cf-tunnel-free
type: finding
status: unverified
date: 2026-10-13
title: Cloudflare Tunnel は無料で使え、ドメインを Cloudflare の DNS に置く必要がある
sources:
  - https://flaviocopes.com/cloudflare-tunnel/
  - https://dev.to/realchaika/how-to-setup-a-cloudflare-tunnel-new-using-gui-method-4maf
links:
  - supports: dec-vm-cloudflare
  - supports: dec-own-domain
  - raises: q-cf-tunnel-official
---
VM から外向きにだけつなぐので、受け口のポートを開けなくてよい。外向きの 7844 番を使う。制限の数値は資料で食い違う。
