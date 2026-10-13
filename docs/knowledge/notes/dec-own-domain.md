---
id: dec-own-domain
type: decision
status: proposed
date: 2026-10-13
title: 独自ドメインを取り、画面と API を同じドメインの下に置く
sources:
  - docs/service-roadmap.md
links:
  - affects: comp-frontend
  - depends_on: q-domain
verifies:
  - S04
  - S09
---
Tunnel に要るうえ、画面と API が同じサイト扱いになり、別サイトの Cookie として弾かれる心配が消える。年額の費用がかかる。
