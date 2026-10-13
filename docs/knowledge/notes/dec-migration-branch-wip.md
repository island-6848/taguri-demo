---
id: dec-migration-branch-wip
type: decision
status: adopted
date: 2026-10-13
title: 画面の移行は wip-screens-port で進め、段ごとに試験が通ってから master に入れる
sources:
  - https://github.com/island-6848/taguri-demo/tree/wip-screens-port
links:
  - answers: q-migration-branch
  - depends_on: production-branch-master
  - depends_on: dec-migration-owner-push
---
本番の deploy 元は master なので（production-branch-master）、ほかのブランチへの push は本番に出ない。別セッションが push した wip-screens-port（7da8985）に master を合わせ（a89a659）、以後の移行の作業はこのブランチに積む。
master に入れるのは段ごとに、Python との一致の試験が通ってから。移した画面は NATIVE_UI に名前を足すまで本番では使われない（Render への中継のまま）。
注意: wip-screens-port には新しい migration（0011.sql、stage_label 表）がある。master に入れると Workers Builds が本番の D1 に当てる。表を足すだけで既存の表は変えないが、入れる前に中身を確かめる。
