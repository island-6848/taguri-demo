---
id: workers-builds-free-3000
type: finding
status: confirmed
date: 2026-10-13
title: Workers Builds（GitHub からの自動配信）は無料プランで月 3,000 分・同時 1 本・1 回 20 分まで
sources:
  - https://developers.cloudflare.com/workers/ci-cd/builds/limits-and-pricing/
links:
  - supports: dec-free-tier-only
---
Cloudflare の公式の表（検索結果の引用で確かめた）。有料プランは月 6,000 分で、越えると 1 分 0.005 ドル。たぐりの配信は 1 回 1〜2 分で、master に押すたびに 1 回なので、1 日 30 回押しても月 1,800 分に収まる。無料プランで 3,000 分を越えたときに止まるのか請求されるのかは、この検索では書かれていなかった（無料プランには支払いの設定が無いので、止まると考えている。未確認）。
