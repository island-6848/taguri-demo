---
id: q-r2-ledger-reconcile
type: question
status: open
date: 2026-10-18
title: R2 の控え（台帳）の数を、Cloudflare が数えた保存と操作の数と突き合わせられるか
links:
  - depends_on: free-tier-audit-1018
  - affects: r2-free-tier-billed
---
R2 を上限の手前で止める仕組みは、取得の作業データの控え（data/free_tier/usage.json）と管理画面の控えだけが頼り。控えが壊れる・古いものに戻ると少なく数え、越えると請求される。Cloudflare の GraphQL Analytics（R2 の保存と操作の数）を Free-tier check で読み、控えと大きい方で点検する案。調べること: 使える API と鍵の権限（Account Analytics の読み取り）、数が出るまでの遅れ、無料で使えるか。
