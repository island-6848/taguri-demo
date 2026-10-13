---
id: dec-defer-workers
type: decision
status: superseded
date: 2026-10-13
title: Cloudflare Workers への完全移行は今は見送る（見直し中）
sources:
  - docs/service-roadmap.md
links:
  - affects: comp-recommender
  - depends_on: q-direction
---
サーバーと DB まわりの書き直しと、おすすめの事前計算化が要り、サービス化が止まる、と判断した。ただし同じ日に、別の作業で Workers＋D1 の版が事前計算の索引まで含めて進んでいることが分かった（workers-d1-preview-state）。書き直しの費用の多くは既に払われつつあるので、採用から「提案」に戻し、q-direction で決め直す。
（2026-10-13、起案者が Workers＋D1 に寄せると決めた）置き換え済み。
