---
id: title-key-parity
type: finding
status: confirmed
date: 2026-10-13
title: 題名の正規化（title_key）は JS でも Python と同じにできる
sources:
  - https://github.com/island-6848/taguri-demo/blob/cloudflare-d1-preview/cloudflare/src/stage-search.js
  - https://github.com/island-6848/taguri-demo/blob/cloudflare-d1-preview/cloudflare/test/stage-search.test.js
---
3,000 件余りの題名（全角・BOM・制御文字・語末の Σ を含む）で一致。Python の \s と strip は JS の \s と範囲が違う（U+001C〜001F・U+0085 を含み U+FEFF を含まない）ので、文字の範囲を明示した。
