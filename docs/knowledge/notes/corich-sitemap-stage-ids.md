---
id: corich-sitemap-stage-ids
type: finding
status: confirmed
date: 2026-10-13
title: CoRich のサイトマップには、すべての公演ページ（/stage/<id>）が更新日つきで載っている
sources:
  - https://github.com/island-6848/taguri-crawler/actions/runs/38403569197（非公開）
  - https://stage.corich.jp/sitemaps/sitemap.xml.gz
links:
  - answers: q-corich-sitemap
  - affects: dec-crawler-gha-private
verifies:
  - S24
---
サイトマップの索引は 10 個のファイルを指し、毎日（深夜 1 時台）作り直されている。sitemap1 は 50,000 件で、うち 49,998 件が公演ページ（/stage/1〜/stage/53815）、すべてに更新日（lastmod）がある。sitemap10 は利用者のページ（/user/<id>）。
公演ページそのものは GitHub Actions から読める（200）ので、**検索ページを使わずに、サイトマップで新しい公演の id を見つけ、公演ページを 1 件ずつ読めば、CoRich だけで公演一覧を作れる。**
残り（sitemap2〜9 の中身、最新の公演 id がどれか、新しい公演が 1 日に何件増えるか、lastmod が公演の更新を表すか）は未確認。
