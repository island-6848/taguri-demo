---
id: corich-robots-sitemap-only
type: finding
status: confirmed
date: 2026-10-13
title: CoRich の robots.txt は禁止を書いておらず、サイトマップを 2 つ示している
sources:
  - https://github.com/island-6848/taguri-crawler/actions/runs/38403367059（非公開）
  - https://stage.corich.jp/robots.txt
links:
  - affects: q-source-terms
  - supersedes: corich-robots-unchecked
verifies:
  - S24
---
GitHub Actions から読んだ stage.corich.jp/robots.txt は 200 で、中身は Sitemap の 2 行（/sitemap.xml と /sitemaps/sitemap.xml.gz）だけ。Disallow は無い。
