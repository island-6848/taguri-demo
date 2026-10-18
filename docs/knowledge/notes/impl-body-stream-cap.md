---
id: impl-body-stream-cap
type: finding
status: confirmed
date: 2026-10-18
title: Native 画面の本文（readInput）は全部読んでから大きさを見ていた。読みながら上限で止める共通の関数（src/body-limit.js）にした
sources:
  - https://github.com/island-6848/taguri-demo/issues/123
  - cloudflare/src/body-limit.js
  - cloudflare/src/screens/index.js
  - cloudflare/src/worker.js
  - cloudflare/test/body-limit.test.js
links:
  - depends_on: sec-audit-1017
---
issue #123。`screens/index.js` の `readInput` は `request.arrayBuffer()` で本文を全部読んでから 8 KB（account は 64 KB）を確かめていた。Content-Length が無いか小さく偽ってあると、大きな本文をそのまま抱えられた。

- `readCapped(request, cap)` を足した。塊ごとに数え、上限を越えた時点で `reader.cancel()` して null を返す。`readInput` と、通常 API の `body()`（worker.js、上限 MAX_BODY）の両方がこれを使う。
- 試験（`test/body-limit.test.js`）：Content-Length 無し・小さく偽った Content-Length・4096 バイトの塊の連続・account の 64 KB ちょうどと超過・8 KB ちょうど。上限を越えたら、読み取りをやめて流れを閉じることを確かめる。

使う量は増えない（読む量が減るだけ）。本番での負荷試験はしていない。
