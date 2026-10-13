---
id: workers-d1-preview-state
type: finding
status: confirmed
date: 2026-10-13
title: 別の作業で、Workers＋D1 の版が workers.dev で動き始めている
sources:
  - https://github.com/island-6848/taguri-demo/tree/cloudflare-d1-preview/cloudflare
links:
  - contradicts: dec-defer-workers
  - affects: q-direction
  - affects: comp-recommender
verifies:
  - S10
  - S20
---
ブランチ cloudflare-d1-preview。Workers の無料プランと D1、ログインは Firebase（Google・メールのリンク）とパスキー、アカウントの完全削除（R7）、推薦は利用者によらない索引を前もって作り D1 に入れ、Worker が本人の分だけ計算して保存する。独自ドメインは使わない。ただし元の 17 画面はまだ Render へ橋渡ししており（ORIGINAL_UI_BRIDGE=true）、Render は止められない。
