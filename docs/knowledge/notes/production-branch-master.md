---
id: production-branch-master
type: finding
status: confirmed
date: 2026-10-13
title: 本番の Worker の公開元を master に切り替えた（PR #5 は master にマージ済み）
sources:
  - https://github.com/island-6848/taguri-demo/commit/669e6dc
links:
  - answers: q-production-branch
  - supersedes: pr-branch-is-production
  - affects: q-migration-branch
verifies:
  - S33
---
PR #5（cloudflare-d1-preview）は master にマージされた（669e6dc、リポジトリで確認）。Cloudflare の設定で本番ブランチを master にしたことは起案者の報告で、管理画面はこの作業環境から見られないので確かめていない。PR のブランチに push しても本番に出ないことの確認（S33）はまだ。
