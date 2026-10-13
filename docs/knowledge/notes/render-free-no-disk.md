---
id: render-free-no-disk
type: finding
status: confirmed
date: 2026-10-13
title: Render の無料プランは永続ディスクを付けられない
sources:
  - https://render.com/docs/free
links:
  - supports: dec-vm-cloudflare
  - answers: q-render-free-viable
  - affects: comp-state-storage
verifies:
  - S02
---
無料の Web サービスはファイルの変更が再デプロイ・再起動・スリープで消える。永続ディスクは有料のサービスだけ。サービス版は永続ディスクが無いと起動しないので、無料プランでは動かせない。
