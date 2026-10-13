---
id: no-ec2
type: finding
status: confirmed
date: 2026-10-13
title: EC2 は無い
sources:
  - https://claude.ai/code/session_015xXsQ9C4423EMquRbg7m3U（起案者の回答）
links:
  - answers: q-ec2-cost
  - raises: q-catalog-source
  - affects: q-crawler-host
  - affects: q-real-catalog-stats
  - affects: dec-render-full-migration
  - affects: comp-catalog-pipeline
verifies:
  - S23
---
起案者の回答（2026-10-13）。これまでの文書（カタログの定期更新・推薦の索引作り・持ち主専用の機能）は EC2 で動かす前提で書かれていたが、その機械は無い。そのため、公演カタログを毎日作り直す処理も、推薦の索引を作る処理も、今はどこでも動いていない可能性が高い。公開版が読む S3 のカタログ（stage-catalog/data.tar.gz）は、いつ・どこで作られたものかを確かめていない。
