---
id: oracle-always-free
type: finding
status: unverified
date: 2026-10-13
title: Oracle Always Free は ARM の VM とディスクが無料。ただし放置判定で回収されうる
sources:
  - https://braindetox.kr/en/posts/oracle_always_free_tier_reduced_2026.html
  - https://terminalbytes.com/oracle-cloud-free-tier-changes-2026
  - https://space-node.net/blog/oracle-cloud-free-vps-guide-2026
links:
  - raises: q-oracle-official
  - supports: dec-vm-cloudflare
---
7 日間の CPU・ネットワーク・メモリの使用が少ないと回収の対象になりうる。2026 年 6 月に ARM の無料枠が 4 OCPU/24GB から 2 OCPU/12GB に減ったという報告があるが、公式の発表は見つからなかった。
