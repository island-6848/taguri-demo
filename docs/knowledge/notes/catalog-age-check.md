---
id: catalog-age-check
type: finding
status: confirmed
date: 2026-10-13
title: カタログの日付は、公開の /api/health と毎日の GitHub Actions で確かめられるようにした
sources:
  - tools/lib/catalog_info.py
  - tools/taguri/check_catalog_age.py
  - .github/workflows/catalog-age.yml
links:
  - affects: q-catalog-source
  - affects: q-monitoring
verifies:
  - S23
---
サーバーは S3 からカタログを取り込むときに、S3 に置かれた時刻と、カタログの中の最新ファイルの時刻を残し、/api/health で返す（日付と件数だけ）。tools/taguri/check_catalog_age.py と .github/workflows/catalog-age.yml が毎日それを読み、3 日より古いか、これからの公演が 100 件未満なら失敗して持ち主に通知が届く。サーバーが新しいコードで起動し直すまでは日付が出ない。作業環境から Render には接続できないので、実際の値は GitHub Actions で見る。
