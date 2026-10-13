---
id: q-crawler-host
type: question
status: open
date: 2026-10-13
title: 公演情報の取得処理をどこで動かすか
links:
  - depends_on: q-ec2-cost
verifies:
  - S23
  - S24
---
候補: 今の EC2（費用は q-ec2-cost）、GitHub Actions（無料だがログが公開・60 日で止まる・github-actions-public-free）、Oracle の無料 VM、Workers の定期実行（1.1 秒に 1 回の丁寧な取得を長く続けられるかは未確認）。どの基盤に寄せても要る。
