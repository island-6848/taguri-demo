---
id: q-real-catalog-stats
type: question
status: open
date: 2026-10-13
title: 実カタログで、推薦の索引の行数と Worker の CPU 時間がどうなるか
links:
  - depends_on: q-ec2-cost
verifies:
  - S20
  - S21
---
EC2 で `cloudflare/scripts/build_recommend_index.py --stats` を実行し、読む行数・書く行数・CPU 時間を測る。無料プランの 10 ミリ秒と D1 の 1 日 10 万行の書き込みに収まるかで、Workers 版が無料で回るかが決まる。
2026-10-13、EC2 は無いと分かった（no-ec2）。カタログのある場所（S3 か、新しく作る取得処理）で測る。
