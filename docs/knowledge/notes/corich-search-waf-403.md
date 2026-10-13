---
id: corich-search-waf-403
type: finding
status: confirmed
date: 2026-10-13
title: CoRich の検索ページは、サーバー手前のロードバランサーが 403 で断っている（公演ページは 200）
sources:
  - https://github.com/island-6848/taguri-crawler/actions/runs/38403367059（非公開）
links:
  - answers: q-corich-search-refusal
  - affects: dec-crawler-gha-private
verifies:
  - S24
---
GitHub Actions（Microsoft の接続元・AS8075）から、名乗り（taguri-bot）を付けて /stage/search を開くと、応答の server は awselb/2.0 で 403。同じ名乗りで /stage/ は 200。robots.txt は禁止していないので、断っているのはサーバー側の仕組み（データセンターからの接続や名乗りへの規則）とみられる。どちらが理由かは切り分けていない。断られたものは、名乗りや接続元を変えてすり抜けない（dec-polite-crawling）。代わりに、robots.txt が示すサイトマップから公演ページを見つける方法を調べる。
