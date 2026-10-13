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
2026-10-13 追記（https://github.com/island-6848/taguri-crawler/actions/runs/38404141838、非公開）: 公演ページが載るのは sitemap1〜3 だけ（1: 49,998 件・id 1〜53815、2: 50,000 件・53816〜107046、3: 41,635 件・107047〜512453）。4〜10 は公演以外。最新の id は 512453 で、新しい id は 33 ずつ飛んで振られている（512321, 512354, …）。
公演ページの欄: 期間・劇場・団体／劇場・出演・演出・脚本・スタッフ・料金（1枚あたり）・公式／劇場サイト・タイムテーブル・その他注意事項など。題名は <title> から取る。都道府県の欄は無い（ページ内のどこに出るかは確認中）。
