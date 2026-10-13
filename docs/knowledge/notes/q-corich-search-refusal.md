---
id: q-corich-search-refusal
type: question
status: answered
date: 2026-10-13
title: CoRich の検索ページが断る理由と、代わりに公演一覧をどこから取るか
links:
  - depends_on: gha-first-run-corich-search-403
  - affects: q-source-terms
verifies:
  - S11
  - S24
---
robots.txt で検索が禁止されているなら、それに従い検索を使わない。データセンターからの接続を一律に断っているなら、許可を問い合わせるか、別の一覧（ステイジーズカレンダー・公演ページの新着など）で候補を作る。名乗りや接続元を偽って続けることはしない（dec-polite-crawling）。
答え（理由）: robots.txt は禁止しておらず、サーバー手前の仕組みが断っている（corich-search-waf-403）。代わりの一覧はサイトマップを調べる（q-corich-sitemap）。
