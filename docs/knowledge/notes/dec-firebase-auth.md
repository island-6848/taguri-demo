---
id: dec-firebase-auth
type: decision
status: adopted
date: 2026-10-13
title: 会員ログインは Firebase Authentication にする
links:
  - affects: comp-firebase-login
  - raises: q-firebase-key-restriction
  - raises: q-firebase-free-tier
---
起案者が比較表を見て選んだ。理由は無料枠の大きさと、パスワードを自分で持たないこと（漏えいの面を小さくする）。WorkOS なども比べた（比較の数値は会話の中の一覧で、一次資料では未確認）。
