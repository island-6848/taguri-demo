---
id: dec-edition-split
type: decision
status: adopted
date: 2026-10-12
title: デモ版とサービス版を分ける
sources:
  - docs/editions.md
links:
  - affects: comp-public-server
  - affects: comp-frontend
verifies:
  - S01
  - S09
---
1 つのフラグ（demo_mode）が公開運用とデモの振る舞いを兼ねていたのを、`public` と `edition` に分けた。サーバー・保存先・合言葉も別にする。
