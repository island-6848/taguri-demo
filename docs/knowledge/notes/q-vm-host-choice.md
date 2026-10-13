---
id: q-vm-host-choice
type: question
status: open
date: 2026-10-13
title: サービス版の VM は Oracle Always Free と今の EC2 のどちらにするか
links:
  - depends_on: q-oracle-payg
  - depends_on: q-ec2-cost
  - depends_on: q-direction
verifies:
  - S12
---
Oracle: 2 OCPU・12GB まで無料だが、使用が少ないと回収されうる（oracle-always-free）。従量課金にしたときの扱いは未確定（q-oracle-payg）。EC2: 新しい口座なら 6 か月のクレジット、無料枠の外なら月 12 ドル以上の見込み（ec2-tokyo-price・aws-ipv4-charge）。今の口座の状態は未確認（q-ec2-cost）。そもそも VM で行くかは q-direction 次第。
