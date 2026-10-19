---
id: dec-entity-pages-keep
type: decision
status: adopted
date: 2026-10-19
title: おすすめ理由の太字のリンク（人物・形式のページ）は、作った形のまま残す
sources:
  - cloudflare/src/screens/entity.js
  - cloudflare/src/screens/recommend.js
links:
  - supersedes: dec-entity-pages-later
  - depends_on: dec-entity-pages
  - affects: comp-cf-worker
---
起案者の指示（2026-10-19）「おすすめ理由のリンクにする対象、やっぱ実装してくれたんならそのまま残しておいて」。先送り（〔dec-entity-pages-later〕、取り消しのコミット 29e9db0）をさらに取り消し、8260cc2 の形に戻した。

- 人物の太字 → `/recommend/person`、形式の太字 → `/recommend/kind`。中身は〔dec-entity-pages〕のとおり
- その前に起案者は「人物だけでよい」とも言っていたが、今回は「そのまま」なので形式のリンクも残した。形式を外すかは起案者に確かめる
- 経歴・プロフィールを外から取るかは、まだ決めていない〔q-entity-pages-next〕
