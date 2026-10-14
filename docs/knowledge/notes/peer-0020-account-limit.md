---
id: peer-0020-account-limit
type: finding
status: confirmed
date: 2026-10-14
title: ログイン修正のセッション（PR #17、master に入った）が、0020 で利用者 100 人の上限トリガーを外し、1 日あたりの新規の上限で抑える形に変えた
sources:
  - https://github.com/island-6848/taguri-demo/blob/claude/demo-records-setup-yqo65u/cloudflare/migrations/0020.sql
  - https://github.com/island-6848/taguri-demo/blob/claude/demo-records-setup-yqo65u/docs/knowledge/notes/dec-login-hardening.md
links:
  - affects: q-account-limit-100
  - supports: dec-login-hardening
---
ブランチ claude/demo-records-setup-yqo65u のコミット 93f3567（2026-10-14）。0020.sql は `DROP TRIGGER IF EXISTS account_limit`。新規は NEW_ACCOUNTS_PER_DAY（src/rate-limit.js）で抑えるとある。そのセッションからの連絡では PR #17 で入れる予定で、マイグレーションは 0021 から使ってほしいとのこと。
q-account-limit-100（起案者に決めてもらう問い）とつながるので、起案者に伝える。上限を外したときに D1 の保存 5 GB・書き込み 1 日 10 万行に収まるかは、そのブランチの記録ではまだ数えていない（読んだ範囲では見当たらない）。2026-10-14 に PR #17 として master に入った（c759dea）。そのセッションの記録（dec-login-hardening）では、起案者が調べた結果の修正を指示したとある。q-account-limit-100 は、無料枠に収まるかを数えてから起案者に確かめるまで open のままにする。
