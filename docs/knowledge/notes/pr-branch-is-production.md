---
id: pr-branch-is-production
type: finding
status: outdated
date: 2026-10-13
title: 本番の Worker は PR のブランチ（cloudflare-d1-preview）から自動で deploy されている
sources:
  - https://github.com/island-6848/taguri-demo/blob/cloudflare-d1-preview/docs/cloudflare-security-review.md
links:
  - raises: q-production-branch
---
レビュー前の変更がそのまま本番に出る。セキュリティ点検で S2（高）とした。
2026-10-13 に master へ切り替えたと起案者から報告があった（production-branch-master）。
