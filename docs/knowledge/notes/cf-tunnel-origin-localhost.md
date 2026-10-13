---
id: cf-tunnel-origin-localhost
type: finding
status: unverified
date: 2026-10-13
title: Tunnel の後ろのサーバーからは、すべての接続元が自分自身に見える
sources:
  - https://dev.to/realchaika/how-to-setup-a-cloudflare-tunnel-new-using-gui-method-4maf
links:
  - affects: comp-auth-throttle
  - raises: q-cf-connecting-ip-trust
verifies:
  - S13
---
本当の接続元は `CF-Connecting-IP` ヘッダで渡される。今の試行回数の制限はこのままだと全員で 1 つの枠を使う。
