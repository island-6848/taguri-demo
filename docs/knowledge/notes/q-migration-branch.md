---
id: q-migration-branch
type: question
status: answered
date: 2026-10-13
title: 移行の作業をどのブランチで進めるか（cloudflare-d1-preview は push すると本番に出る）
links:
  - depends_on: q-production-branch
  - affects: migration-handover-stage0
verifies:
  - S33
---
cloudflare-d1-preview は push するとそのまま本番へ deploy され、D1 の migrations も自動で当たる（pr-branch-is-production）。移行の途中の変更をここへ直接 push すると本番が壊れうる。本番の deploy 元を master に変えるか、作業用の別ブランチで進めて段ごとに合わせる。
