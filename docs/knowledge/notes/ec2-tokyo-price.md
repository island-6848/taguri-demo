---
id: ec2-tokyo-price
type: finding
status: unverified
date: 2026-10-13
title: 東京の t4g.micro は 1 時間 0.0108 ドル（月 8 ドルほど）、t3.micro は 0.0136 ドル
sources:
  - https://aws-pricing.com/t4g.micro.html
  - https://www.doit.com/compute/spot/ap-northeast-1/t3.micro
links:
  - affects: q-ec2-cost
verifies:
  - S12
---
価格の集計サイトの値。公開 IPv4（月 3.6 ドル）とディスク代（未調査）が別にかかる。無料枠の外なら、t4g.micro でも月 12 ドル以上と見込まれる。
