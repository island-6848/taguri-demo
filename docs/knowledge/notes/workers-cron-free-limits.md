---
id: workers-cron-free-limits
type: finding
status: confirmed
date: 2026-10-13
title: Workers の定期実行は、無料プランだと 1 回あたり CPU 10 ミリ秒・外部への要求 50 回まで
sources:
  - https://developers.cloudflare.com/workers/platform/limits
  - https://developers.cloudflare.com/workflows/reference/limits
  - https://cronuru.com/guides/cloudflare-workers-cron-triggers
links:
  - affects: q-crawler-host
verifies:
  - S23
---
通信の待ち時間は CPU 時間に数えない。1 回の実行は最長 15 分（壁時計）。有料プランは外部への要求が 1 回 1 万回まで。定期実行はアカウントで 5 個まで（無料、二次情報）。今の取得処理は Python で、毎日数十〜数百件、日曜は数百件以上を 1.1 秒おきに取る。無料プランでは 1 回 50 回の要求で区切って何度も回し、JS に移す必要がある。（公式ページの記述を検索結果の引用で確かめた。作業環境の通信制限でページを直接は開けていない）
