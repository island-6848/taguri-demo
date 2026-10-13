---
id: d1-free-limits
type: finding
status: confirmed
date: 2026-10-13
title: D1 の無料枠は 1 日に読み 500 万行・書き 10 万行、保存 5GB
sources:
  - https://developers.cloudflare.com/d1/platform/pricing/
links:
  - affects: q-d1-python-workers
  - affects: q-direction
verifies:
  - S20
  - S21
---
上限は毎日 0 時（UTC）に戻り、達するとその日は問い合わせがエラーになる。保存が 5GB に達すると、消すまで書き込めない。読んだ行は「走査した行」で数える（全件走査は全件分）。（公式ページの記述を検索結果の引用で確かめた。作業環境の通信制限でページを直接は開けていない）
