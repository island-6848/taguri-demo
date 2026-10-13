---
id: q-cf-connecting-ip-trust
type: question
status: dropped
date: 2026-10-13
title: CF-Connecting-IP をどう信頼するか
verifies:
  - S13
---
cloudflared からの接続（127.0.0.1）のときだけヘッダを信じ、それ以外は無視する形でよいか。ヘッダを偽れないことを確かめる。
（2026-10-13、起案者が Workers＋D1 に寄せると決めた）VM＋Cloudflare の案に固有の問いなので取り下げた。
