---
id: gha-private-free-minutes
type: finding
status: confirmed
date: 2026-10-13
title: 非公開リポジトリの GitHub Actions は、無料アカウントで月 2,000 分まで無料
sources:
  - https://docs.github.com/en/billing/concepts/product-billing/github-actions
links:
  - affects: q-crawler-host
verifies:
  - S12
---
超えた分は、支払いの上限が既定で 0 ドルなので止まるだけで請求されない。日次 20 分・週次 60 分なら月 900 分ほどで収まる見込み（取得の所要時間は未測定）。1 つのジョブの上限（6 時間）は今回の検索では確かめられなかった（以前からの知識）。
2026-10-13 追記: 実測では毎日の Catalog が 1 回 約 9 分、初回の 6,000 枚が 196 分（crawler-actions-minutes）。過去の公演を 1 日 6,000 枚読むと収まらないので、上限（直近 31 日で 1,500 分）の中で読む量を決めるようにした（dec-free-tier-only）。
