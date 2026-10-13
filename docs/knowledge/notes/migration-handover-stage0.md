---
id: migration-handover-stage0
type: finding
status: confirmed
date: 2026-10-13
title: Render からの画面移行は段 0 まで済み、段 1 の途中は別セッションの手元にしかない
sources:
  - https://github.com/island-6848/taguri-demo/commit/1b2571f
  - https://github.com/island-6848/taguri-demo/blob/cloudflare-d1-preview/docs/render-migration-plan.md
links:
  - affects: dec-render-full-migration
  - raises: q-migration-owner
  - raises: q-migration-branch
---
段 0（cloudflare-d1-preview 1b2571f）: 元の画面の利用者ごとの表（migrations/0010.sql）、NATIVE_UI で有効にした画面だけ Worker が答える振り分け（本番は未設定）、Python 互換の小物、Python の画面を一時保存先・固定日付・通信なしで動かして応答を書き出す試験と、同じ手順を Worker で流して比べる試験。コミットはリモートで確かめた。
段 1 の途中（評価・未評価・感想の画面と add_work・rate・note、約 1000 行、試験はまだ通らない）は、別セッションの作業環境のローカルブランチ wip-screens-port にしか無い（リモートに無いことを確かめた）。
別セッションの連絡によると、起案者の指示で移行の続きはこの（Push）セッションに任され、別セッションは推薦の計算の改善を続ける。この指示は起案者から直接はまだ聞いていない。
