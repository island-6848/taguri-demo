---
id: cf-free-tier-snippets-1018
type: finding
status: confirmed
date: 2026-10-18
title: 公式の料金表（検索結果の引用）で、R2 の消す操作は無料・D1 の保存は口座の全 D1 の合計で索引も入る・Workers 無料は 1 日 10 万要求で定期実行も CPU 10 ミリ秒・Actions はジョブごとに分へ切り上げ
sources:
  - https://developers.cloudflare.com/r2/pricing/
  - https://developers.cloudflare.com/d1/platform/pricing/
  - https://developers.cloudflare.com/workers/platform/limits/
  - https://developers.cloudflare.com/workers/platform/pricing/
  - https://docs.github.com/en/billing/concepts/product-billing/github-actions
links:
  - supports: free-tier-audit-1018
  - supports: r2-free-tier-billed
  - supports: d1-free-limits
  - raises: q-rate-limit-binding-pricing
---
issue #139 の点検で確かめ直した。**公式ページそのものは開けていない**（この作業環境では WebFetch が developers.cloudflare.com・docs.github.com の名前解決に失敗する、cf-docs-blocked-here）。以下はすべて公式ページを検索結果の引用で見たもの。

- R2: 無料は Standard の保存 10 GB-月・Class A 月 100 万回・Class B 月 1,000 万回。消す操作（Delete）は無料（引用は料金ページの試し版から）。取り出しの通信料は無料
- D1: 無料は 1 日 読み 500 万行・書き 10 万行・保存 5 GB。0 時（UTC）に戻る。保存は口座のすべての D1 の合計で、表と索引の両方が入る。索引のある列を書くと、表と索引で 2 行に数える。越えるとその日は問い合わせがエラーになる
- Workers 無料: 1 日 10 万要求（静的ファイルは数えない）、1 回 CPU 10 ミリ秒（定期実行も同じ）、定期実行は口座で 5 個、外への要求は 1 回 50 まで
- GitHub Actions: 無料のアカウントは非公開リポジトリで月 2,000 分。ジョブごとに分へ切り上げる。公開リポジトリの標準の実行環境は無料。支払いの上限 0 ドル（既定）だと、使い切ったあとは使えない

分からなかったこと: PutBucketLifecycleConfiguration・バケットの GET が Class A・B のどちらか（たぐりは多めの側に数える）。定期実行が 1 日 10 万要求に数えられるか。Rate Limiting の結び付けの料金（q-rate-limit-binding-pricing）。
