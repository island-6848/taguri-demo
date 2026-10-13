---
id: gha-public-logs
type: finding
status: unverified
date: 2026-10-13
title: 公開リポジトリの Actions の実行ログは誰でも読める。成果物はログインした人が取れる
sources:
  - https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts
links:
  - affects: q-crawler-host
  - affects: catalog-terms-no-redistribution
---
公式文書では、成果物はログインして読む権限のある人が取れる。公開リポジトリならログインしていれば誰でも読める。ログはログインなしで読めるはず（以前からの知識で、今回は確かめていない）。公演カタログ（再配布しない約束）をログや成果物に出さない作りが要る。保存期間の既定は 90 日。
