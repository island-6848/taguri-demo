---
id: d1-free-write-limit
type: finding
status: unverified
date: 2026-10-13
title: D1 の無料枠は 1 日 10 万行の書き込み・500 万行の読み込み（記憶による数値）
sources:
  - https://developers.cloudflare.com/d1/platform/pricing/
links:
  - answers: q-d1-python-workers
  - raises: q-real-catalog-stats
  - supports: d1-free-limits
---
索引を入れ直すと全行を書き、古い版を消すときにもう一度数える。公演の題名検索の表（rec_gram）も足したので、実カタログの --stats の rows_written を見て判断する。
