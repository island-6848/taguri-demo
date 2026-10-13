---
id: comp-public-server
type: component
status: current
date: 2026-10-13
title: 公開版のサーバー（serve_cloud.py・serve.py）
sources:
  - tools/taguri/serve_cloud.py
  - tools/taguri/serve.py
---
公開版の入口。`TAGURI_EDITION` で版を決め、Cookie と復旧コードで利用者を分ける。標準ライブラリの http.server と SQLite で動く。
