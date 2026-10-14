---
id: d1-meta-size-after
type: finding
status: confirmed
date: 2026-10-14
title: D1 は問い合わせの結果の meta に size_after（コミット後の DB の大きさ・バイト）、rows_read・rows_written（索引の行を含む）を返す
sources:
  - https://developers.cloudflare.com/d1/worker-api/return-object/
  - https://developers.cloudflare.com/api/operations/cloudflare-d1-raw-database-query
links:
  - supports: dec-account-cap-counted
---
公式の文書（Worker API の return object と REST API の raw query）に、meta の欄として changed_db・changes・rows_read（索引の行を含む。返した行より多くなりうる）・rows_written（索引の書き込みを含む）・size_after（コミット後の DB の大きさ、バイト）がある。Worker API には total_attempts もある。
**公式ページは検索結果の引用でしか見ていない**（この作業環境からは developers.cloudflare.com を開けない）。本番で size_after が SELECT にも付くかは確かめていない（付かなければ d1Bytes は null を返し、書き込みは止めない作り）。
