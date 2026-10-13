---
id: q-worker-posters
type: question
status: answered
date: 2026-10-13
title: Cloudflare 版でポスターをどこに置いて出すか
sources:
  - tools/taguri/posters.py
  - cloudflare/src/screens/rate.js
links:
  - depends_on: dec-recommend-compact-poster
---
Python 版は更新の段でポスターを端末内に取り込み、画面には `/img/<id>` だけを書く（`tools/taguri/posters.py`、画面から外部を叩かない守り）。Cloudflare 版は `posterHtml()` がまだ空文字を返す（`cloudflare/src/screens/rate.js`）── 置き場（R2 か Workers の静的資産か）と、取り込みをクローラ（taguri-crawler）のどの段で行うかが決まっていない。
