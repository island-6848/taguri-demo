---
id: d1-free-limits
type: finding
status: unverified
date: 2026-10-13
title: D1 の無料枠は日ごとの読み書き上限（数値は未確認）
sources:
  - https://developers.cloudflare.com/d1/reference/faq
  - https://eastondev.com/blog/en/posts/dev/20260526-cloudflare-free-limits/
links:
  - raises: q-d1-python-workers
---
上限に達するとその日は問い合わせが失敗する、と公式の FAQ にある。具体的な数値は資料によって食い違う。
