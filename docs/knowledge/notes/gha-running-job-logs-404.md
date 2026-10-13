---
id: gha-running-job-logs-404
type: finding
status: confirmed
date: 2026-10-13
title: 実行中の GitHub Actions のジョブのログは API で取れない（404）。進み具合は手順の状態でしか見えない
sources:
  - https://github.com/island-6848/taguri-crawler/actions/runs/38404782069
links:
  - affects: dec-crawler-gha-private
---
2026-10-13 13:47 UTC に、taguri-crawler の Catalog（サイトマップ版の初回、13:25 開始）のログを取ろうとすると HTTP 404 が返った。ジョブの手順の状態は取れ、「Rebuild the catalog」が 13:25:17 から実行中だった。
そのため「公演ページ n/6000」の進み方は終わるまで見えない。見積もり（1.1 秒に 1 件で 6,000 件、2 時間弱）どおりなら 15:30 UTC ごろに終わる。終わるまでの進み具合を見たいなら、途中経過を手順の要約（GITHUB_STEP_SUMMARY）に書くなどの工夫が要る（まだしていない）。
