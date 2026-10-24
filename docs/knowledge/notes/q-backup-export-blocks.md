---
id: q-backup-export-blocks
type: question
status: open
date: 2026-10-24
title: 毎日の控え（backup_d1.py）は wrangler d1 export を使う。export のあいだ D1 が答えなくなるなら、夜に数十秒サイトが止まっているのではないか
sources:
  - cloudflare/scripts/backup_d1.py
  - https://developers.cloudflare.com/api/resources/d1/subresources/database/methods/export/
links:
  - raises: dec-reco-nightly
---
Cloudflare の D1 の export の API の説明に「大きな書き出しには時間がかかり、そのあいだ D1 は問い合わせに答えない」とある（検索結果の引用で確かめた。ページは直接開けていない）。wrangler d1 export がこの API を使うかは確かめていない。

確かめること: Catalog の「Back up the user records」の段の時間と、その時刻に Worker が 5xx を返していないか。止まるなら、利用者の表を SELECT で読む形（nightly_reco.mjs と同じ）に替える。
