---
id: q-vm-host-choice
type: question
status: open
date: 2026-10-13
title: サービス版の VM は Oracle Always Free と今の EC2 のどちらにするか
links:
  - depends_on: q-oracle-official
  - depends_on: q-ec2-cost
verifies:
  - S12
---
費用・回収の心配・取得処理を同じ VM に載せられるかで決める。同じ VM に載せれば S3 の受け渡しが要らなくなる。
