---
id: github-actions-public-free
type: finding
status: confirmed
date: 2026-10-13
title: 公開リポジトリでは GitHub Actions の標準の実行環境が無料。ただし 60 日動きが無いと定期実行が止まる
sources:
  - https://docs.github.com/en/actions/reference/usage-limits-billing-and-administration
links:
  - raises: q-crawler-host
---
取得処理をここで回せば機械代はかからない。一方、公開リポジトリの実行ログは誰でも読めるので、公演カタログ（再配布しない約束）や合言葉をログや成果物に出さない作りが要る。取得先から見た接続元が GitHub の共有アドレスになる点も確かめていない。
