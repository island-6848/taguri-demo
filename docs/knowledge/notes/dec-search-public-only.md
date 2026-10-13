---
id: dec-search-public-only
type: decision
status: adopted
date: 2026-10-13
title: 記録を公演に結び付ける検索には、公開カタログの公演だけを出す
sources:
  - https://github.com/island-6848/taguri-demo/blob/cloudflare-d1-preview/cloudflare/src/stage-search.js
links:
  - raises: q-past-stage-catalogue
---
持ち主の購入メールから作った過去の公演（credits.jsonl の件名など）を出すと、ほかの利用者に持ち主の観劇歴が見える。そのため古い公演はまだ探せない。
