---
id: q-catalog-to-worker
type: question
status: open
date: 2026-10-13
title: 取得したカタログを Cloudflare 版（D1）にどう届けるか
links:
  - depends_on: q-real-catalog-stats
  - depends_on: no-aws
verifies:
  - S21
  - S23
---
GitHub Actions で作ったカタログから推薦の索引（build_recommend_index.py）と公演一覧を作り、wrangler d1 execute で D1 に入れる。Cloudflare の API トークン（D1 の編集だけの権限）を非公開リポジトリの秘密に入れる。D1 の無料枠（1 日 10 万行の書き込み）に収まるかは索引の行数次第。
