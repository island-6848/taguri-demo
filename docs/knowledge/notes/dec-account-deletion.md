---
id: dec-account-deletion
type: decision
status: adopted
date: 2026-10-13
title: アカウント削除は「削除」の入力と直近 10 分以内のログインを求める
sources:
  - https://github.com/island-6848/taguri-demo/blob/cloudflare-d1-preview/cloudflare/test/account-delete.test.js
links:
  - affects: comp-d1
  - raises: q-firebase-user-deletion
---
D1 の利用者の行を表ごとに明示的に消し（外部キーの連鎖に頼らない）、Google と結び付いていれば Firebase 側の利用者も消す。テストは外部キーを切った状態でも全部消えることを確かめる。
