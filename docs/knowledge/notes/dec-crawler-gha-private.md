---
id: dec-crawler-gha-private
type: decision
status: proposed
date: 2026-10-13
title: 取得処理は、非公開の別リポジトリの GitHub Actions で動かす（勧め）
sources:
  - docs/service-roadmap.md
links:
  - affects: q-crawler-host
  - depends_on: gha-private-free-minutes
  - depends_on: gha-public-logs
  - depends_on: crawler-state-between-runs
verifies:
  - S23
  - S24
---
理由: 今の Python のコードがそのまま動く／月 2,000 分の無料枠に収まる見込み／ログと成果物が公開されない（公開リポジトリだとカタログがログから漏れうる）。非公開リポジトリのワークフローが公開リポジトリのコードを取り出して動かし、前回までのカタログと控えを S3（既存）か R2 から戻し、終わったら載せ直す。推薦の索引は wrangler で D1 に入れる。弱み: 定期実行が遅れる・飛ばされることがある（カタログの日付の監視で気付く）。Workers の定期実行は、無料だと 1 回 50 要求までで、JS への書き直しも要るので見送る。
