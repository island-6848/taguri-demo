---
id: d1-query-limits
type: finding
status: unverified
date: 2026-10-13
title: D1 は 1 つの問い合わせに 100 個までの値しか渡せず、1 文は 100 KB まで
sources:
  - https://developers.cloudflare.com/d1/platform/limits/
links:
  - affects: comp-rec-index
---
この前提で 49 組（ver＋2×49）ずつ・9 万バイトずつに分けている。Cloudflare の制限の文書に基づく理解だが、この環境からは読み直せていない。
