---
id: throttle-keyed-by-client-address
type: finding
status: confirmed
date: 2026-10-13
title: 試行回数の制限は接続元のアドレスで数えている
sources:
  - tools/taguri/serve.py
  - tools/taguri/auth.py
links:
  - affects: comp-auth-throttle
  - raises: q-cf-connecting-ip-trust
verifies:
  - S13
---
`self.client_address[0]` を鍵にしている。プロキシや Tunnel の後ろでは全員が同じアドレスに見え、20 人が 10 分以内に来ると新規登録が止まり、1 人の総当たりで全員の復旧が止まる。
