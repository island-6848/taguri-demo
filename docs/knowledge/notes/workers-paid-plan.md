---
id: workers-paid-plan
type: finding
status: confirmed
date: 2026-10-13
title: Workers の有料プランは月 5 ドルで、要求 1000 万回・CPU 3000 万ミリ秒・D1 の読み 250 億行が含まれる
sources:
  - https://developers.cloudflare.com/workers/platform/pricing/
  - https://developers.cloudflare.com/d1/platform/pricing/
links:
  - supports: dec-scale-workers
  - affects: q-direction
verifies:
  - S12
---
超えた分は要求 100 万回で 0.30 ドル、CPU 100 万ミリ秒で 0.02 ドル。D1 は月に読み 250 億行・書き 5000 万行・保存 5GB まで含み、超過は読み 100 万行 0.001 ドル・書き 100 万行 1 ドル・保存 1GB 月 0.75 ドル。1 要求の CPU は 30 秒まで。（公式ページの記述を検索結果の引用で確かめた。作業環境の通信制限でページを直接は開けていない）
