---
id: serve-cloud-render-guard
type: finding
status: confirmed
date: 2026-10-13
title: サービス版の保存先の検査が Render を前提にしている
sources:
  - tools/taguri/serve_cloud.py
links:
  - affects: comp-public-server
  - affects: comp-vm-host
verifies:
  - S02
---
Render の外では `TAGURI_ALLOW_LOCAL_SERVICE=1` が無いと起動せず、付けると実ディスクの検査を飛ばす。待ち受けは 0.0.0.0。VM ではディスクの検査を効かせ、127.0.0.1 で待ち受けるよう直す必要がある。
