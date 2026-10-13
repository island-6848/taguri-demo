---
id: comp-auth-throttle
type: component
status: current
date: 2026-10-13
title: 登録・復旧の試行回数の制限（auth.py）
sources:
  - tools/taguri/auth.py
---
新規登録は 10 分に 20 回、復旧は 10 分に 10 回まで。数える単位は接続元のアドレス。
