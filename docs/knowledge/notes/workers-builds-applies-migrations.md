---
id: workers-builds-applies-migrations
type: finding
status: confirmed
date: 2026-10-13
title: push するたびに Workers Builds が D1 の migration を当ててから deploy する
sources:
  - https://github.com/island-6848/taguri-demo/blob/cloudflare-d1-preview/cloudflare/README.md
links:
  - affects: comp-d1
---
Deploy command が `npx wrangler d1 migrations apply taguri-demo --remote && npx wrangler deploy`。そのため GitHub Actions で migration を当てる仕組み（とその API トークン）は要らなかった。作ったトークンは消してもらう。
