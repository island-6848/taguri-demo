---
id: find-starto-robots-no-claude-1024
type: finding
status: confirmed
date: 2026-10-24
title: STARTO の公式サイト（starto.jp）の robots.txt は ClaudeBot・Claude-SearchBot・GPTBot などを全面的に断っている。所属の一覧は公式サイトから取らない
sources:
  - https://starto.jp/robots.txt
links:
  - affects: dec-member-affil-tag
  - depends_on: q-affil-external-list
---
起案者が通信の許可に starto.jp を足した後（2026-10-24）、取得元そのものを見て確かめた。

- `https://starto.jp/robots.txt` には `User-agent: ClaudeBot`・`User-agent: Claude-SearchBot`・`User-agent: GPTBot`・`Amazonbot` などがあり、どれも `Disallow: /`。
- この作業は Claude が行うので、AI による取得を断るという意思表示に従う。見たのはトップページ（どのページがあるかを確かめるため 1 回）と robots.txt だけ。アーティストの一覧のページは取っていない。
- サイトポリシーのページ（/s/p/group/detail/sitepolicy）も取っていない。
- そのため、STARTO の一覧は Wikipedia の分類〔find-wikipedia-member-categories-1024〕と、手元の出演欄の書き添えだけで作る。
