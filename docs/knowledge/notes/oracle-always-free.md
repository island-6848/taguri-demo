---
id: oracle-always-free
type: finding
status: confirmed
date: 2026-10-13
title: Oracle Always Free の ARM は 2 OCPU・12GB まで。使用が少ないと回収されうる
sources:
  - https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm
  - https://www.infoq.com/news/2026/07/oracle-cloud-free-tier-limits/
  - https://linuxiac.com/oracle-quietly-cuts-free-tier-ampere-a1-resources-in-half/
links:
  - answers: q-oracle-official
  - raises: q-oracle-payg
  - supports: dec-vm-cloudflare
verifies:
  - S12
  - S29
---
公式の資料では、ARM（Ampere A1）の無料枠は月 1,500 OCPU 時間・9,000 GB 時間で、常時なら 2 OCPU・12GB にあたる（以前は 4 OCPU・24GB）。7 日間で CPU の 95 パーセンタイル・ネットワーク・メモリ（A1 のみ）がいずれも 20% 未満だと、放置とみなされ回収されうる。たぐりは普段ほとんど CPU を使わないので、この条件に当たりやすい。（公式ページの記述を検索結果の引用で確かめた。作業環境の通信制限でページを直接は開けていない）
