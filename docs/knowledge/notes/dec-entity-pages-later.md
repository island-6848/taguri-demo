---
id: dec-entity-pages-later
type: decision
status: adopted
date: 2026-10-19
title: おすすめ理由の太字のリンク（人物・形式のページ）は先送りにして、いったん元に戻す
sources:
  - https://github.com/island-6848/taguri-demo/commit/8260cc2
links:
  - supersedes: dec-entity-pages
  - affects: comp-cf-worker
---
起案者の指示（2026-10-19）「おすすめ理由のリンクにする対象、人物だけでよい」のあと、「一回先送りでいいや。元に戻して。今後実装したい気持ちはあるけど、まだいいや」。

- コミット 8260cc2（人物・形式のページ、理由の太字のリンク）を取り消した。理由の太字はリンクでない元の形に戻る
- 次に作るときの前提: リンクにするのは**人物だけ**（形式は対象外）。作りかけの形は 8260cc2 の `cloudflare/src/screens/entity.js` にある。〔q-entity-pages-next〕
