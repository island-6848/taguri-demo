---
id: r2-free-tier
type: finding
status: unverified
date: 2026-10-13
title: R2 は 10GB まで無料で、取り出しの通信料がかからない
sources:
  - https://flarecalc.com/calculators/r2
  - https://www.spendbase.co/?p=35561
links:
  - supports: dec-vm-cloudflare
  - raises: q-r2-boto3
  - affects: comp-catalog-pipeline
---
月 10GB・書き込み系 100 万回・読み取り系 1000 万回まで無料、という二次情報。Cloudflare の料金ページでは確かめていない。
