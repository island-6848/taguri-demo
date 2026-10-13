---
id: catalog-daily-splitlines
type: finding
status: confirmed
date: 2026-10-13
title: 最初の毎日の Catalog は D1 に入れる段で落ちた。題名の中の U+2028 を splitlines が行の区切りにしたため（直した）
sources:
  - https://github.com/island-6848/taguri-crawler/actions/runs/38483279440
  - cloudflare/scripts/deliver_catalogue.py
  - cloudflare/test/test_deliver_catalogue.py
links:
  - affects: dec-d1-catalogue-delivery
  - affects: sitemap-first-run
---
2026-10-13 23:16 UTC の定期実行（スケジュールの 19:17 UTC から約 4 時間遅れて始まった。gha-schedule-unreliable）。取り直しは成功（これからの公演 1,352 件・カレンダー 336 件）したが、「Deliver the catalogue to D1」が `json.decoder.JSONDecodeError: Unterminated string`（candidates.jsonl の 1 行目の 104 文字目）で失敗し、**D1 にはまだ何も入っていない**。原因: Python の `str.splitlines()` は `\n` だけでなく U+2028・U+0085 などでも切る。公演の文に U+2028 が入っていた。JSONL を読むところ（deliver_catalogue・deliver_past・convert_catalogue・fetch_past_stages）を `split("\n")` に直し、U+2028 入りの題名の試験を足した。次の毎日の実行（10-14）で入るはず。
この実行は R2 にポスターを入れる段を足す前のコミット（3858efb）で動いたので、R2 にも入っていない。
