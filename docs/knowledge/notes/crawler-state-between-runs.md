---
id: crawler-state-between-runs
type: finding
status: confirmed
date: 2026-10-13
title: 取得処理は前回までの控えを引き継いで動く（毎回まっさらでは動かない）
sources:
  - docs/catalog-refresh.md
  - tools/taguri/fetch_requests.py
  - tools/taguri/favourites.py
links:
  - affects: q-crawler-host
---
お気に入りの検索は 3 日・依頼の検索は 7 日の控えを持ち、日曜は「新しい公演と前回取れなかった分だけ」取る。毎回新しい機械で動かす（GitHub Actions など）なら、前回のカタログと控えをどこかから戻してから始め、終わったら保存する必要がある。
