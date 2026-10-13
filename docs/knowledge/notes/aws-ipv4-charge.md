---
id: aws-ipv4-charge
type: finding
status: confirmed
date: 2026-10-13
title: AWS は公開 IPv4 アドレス 1 つにつき 1 時間 0.005 ドル（月 3.6 ドルほど）かかる
sources:
  - https://aws.amazon.com/blogs/aws/new-aws-public-ipv4-address-charge-public-ip-insights
links:
  - affects: q-ec2-cost
verifies:
  - S12
---
2024 年 2 月から。EC2 に付けた公開アドレスも対象。Tunnel で外向きにだけつなぐなら、公開アドレスを外して IPv6 か NAT にする手もある（未検討）。
