---
id: q-cf-access
type: question
status: dropped
date: 2026-10-13
title: 検証中に自分だけを通す方法（Cloudflare Access の無料枠）
links:
  - depends_on: dec-vm-cloudflare
verifies:
  - S30
---
Render のメンテナンスモードの代わりに、検証中は入口を自分だけに絞る。Cloudflare Access の無料で使える人数と、Tunnel との組み合わせ方を公式文書で確かめる。使えなければ、検証中は DNS の名前を公開しない形にする。
（2026-10-13、起案者が Workers＋D1 に寄せると決めた）VM＋Cloudflare の案に固有の問いなので取り下げた。
