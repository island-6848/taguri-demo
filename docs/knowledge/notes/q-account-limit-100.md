---
id: q-account-limit-100
type: question
status: open
date: 2026-10-14
title: D1 の users 表に「全体で 100 人まで」の歯止め（試験版の名残り）があるが、本番でもこのままにするか
sources:
  - cloudflare/migrations/0001.sql
links:
  - affects: dec-native-cutover-now
  - affects: dec-free-tier-only
---
0001.sql の TRIGGER account_limit が、users が 100 行になると新しい登録を止める（'preview account limit'）。本番の切り替え（dec-native-cutover-now）で、登録した人が実際に使う段になった。
無料枠の点では歯止めとして働く（1 人あたりの保存にも上限がある）。100 人を越えて受け付けるなら、マイグレーション（0017 から）で上限を変え、無料枠（D1 の保存 5 GB・書き込み 1 日 10 万行）に収まるかを数えてからにする。起案者に決めてもらう。
