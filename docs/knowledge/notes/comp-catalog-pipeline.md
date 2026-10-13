---
id: comp-catalog-pipeline
type: component
status: current
date: 2026-10-13
title: 公演カタログの取得と配布（publish_catalog.py）
sources:
  - tools/taguri/publish_catalog.py
  - docs/catalog-refresh.md
---
手元の定期処理が公演情報を取り、まとめて S3 に置く。公開サーバーはそれを読むだけ。
