---
id: no-aws
type: finding
status: confirmed
date: 2026-10-13
title: AWS はもう使っていない
sources:
  - https://claude.ai/code/session_015xXsQ9C4423EMquRbg7m3U（起案者の回答）
links:
  - affects: dec-crawler-gha-private
  - raises: q-render-s3-dependency
  - raises: q-catalog-to-worker
  - affects: q-catalog-source
---
起案者の回答（2026-10-13）。公演カタログの置き場所（S3 の stage-catalog/）を前提にした仕組み（publish_catalog.py の S3 への載せ直し、serve_cloud.py の起動時の取り込み、crawler_state.py の S3 版）は前提が成り立たない。取得処理の作業データは非公開リポジトリの state ブランチに置く形に変えた。
