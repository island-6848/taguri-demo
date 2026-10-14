---
id: workers-builds-master-fail
type: finding
status: outdated
date: 2026-10-13
title: コミットの ✗ は Workers Builds が cloudflare/ の無い master を組もうとして失敗していたため
sources:
  - https://github.com/island-6848/taguri-demo/pull/5
links:
  - affects: comp-cf-worker
---
Cloudflare の Git 連携が master にも走り、設定の無いブランチで失敗していた。
2026-10-14 追記: 今の ✗ はこれとは別（workers-builds-branch-fail）。
