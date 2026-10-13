---
id: aws-free-plan-2025
type: finding
status: confirmed
date: 2026-10-13
title: AWS の無料枠は 2025 年 7 月 15 日以降の新しい口座ではクレジット制（最大 200 ドル・6 か月）
sources:
  - https://aws.amazon.com/about-aws/whats-new/2025/07/aws-free-tier-credits-month-free-plan/
links:
  - affects: q-ec2-cost
verifies:
  - S12
---
新しい口座は登録時に 100 ドル、決められた操作で最大 100 ドルを足して計 200 ドル。無料プランは最長 6 か月かクレジットを使い切るまで。EC2 の利用はこのクレジットから引かれる。以前の「t2/t3.micro を 12 か月・月 750 時間」は、それより前に作った口座だけ。
