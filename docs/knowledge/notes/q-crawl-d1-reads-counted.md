---
id: q-crawl-d1-reads-counted
type: question
status: answered
date: 2026-10-20
title: 取得（taguri-crawler）が D1 から読む行数を、無料枠の点検（free_tier.py check）で数えていない。wrangler の Rows read を控えて、1 日 500 万行の何割かを表に出すか
sources:
  - cloudflare/scripts/free_tier.py
  - https://github.com/island-6848/taguri-crawler/actions/runs/39390407820
links:
  - raises: f-deliver-past-reads
  - affects: d1-free-limits
---
点検の表は、D1 の書き込み（取得の分）・R2・Actions の分を出すが、D1 の読み出しの行は無い。2026-10-20 の取得は、1 つの段だけで 1,527,180 行を読んでいた〔f-deliver-past-reads〕。取得の側の読み出しは、どこにも控えていない（Worker の側の数え方は、この問いでは確かめていない）。
- 調べること: 各段の wrangler d1 execute が返す meta.rows_read を足し、控え（free_tier/usage.json）に日ごとに残せるか。CAPS に取得の読み出しの上限を足すか

追記（2026-10-21）: 〔dec-crawl-tiers〕で答えた。点検の段が、取得の各段の wrangler の出力（tee で残したログ）から rows_read を足して `usage.json` の `d1_reads` に控え、`wrangler d1 info --json` の rows_read_24h（Worker と取得の合計）も表に出す。
