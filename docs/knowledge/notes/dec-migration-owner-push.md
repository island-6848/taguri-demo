---
id: dec-migration-owner-push
type: decision
status: adopted
date: 2026-10-13
title: 画面の移行（段 1〜5）は Push セッションが引き継ぎ、途中のコードも受け取る
links:
  - answers: q-migration-owner
  - depends_on: dec-render-full-migration
  - affects: migration-handover-stage0
---
起案者の指示（2026-10-13、Push セッションで「引き継いでよい。push してもらって受け取る」）。別セッションの手元にある段 1 の途中のコード（wip-screens-port）は、本番に出ないブランチに push してもらって受け取る。別セッションは推薦の計算の改善を受け持つ。
