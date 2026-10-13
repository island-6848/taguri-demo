---
id: python-workers-migration-state
type: finding
status: confirmed
date: 2026-10-13
title: 別の作業で、元の画面の Python を Python Workers で動かす移行版も作られている
sources:
  - https://github.com/island-6848/taguri-demo/blob/cloudflare-complete-migration/docs/verification/2026-10-13-cloudflare-migration-final-review.md
links:
  - affects: q-direction
  - raises: q-d1-python-workers
---
ブランチ cloudflare-complete-migration。元の 17 画面を Python Workers と Durable Object で動かし、D1 に保存する。独立したレビューの判定は「下書きの公開は可、本番の切り替えは不可」。実際の Python Workers での起動、全件の移行、見た目と操作の同等性は未確認。全利用者を 1 つの Durable Object に送る作りで、集中時の待ち時間も未測定。
