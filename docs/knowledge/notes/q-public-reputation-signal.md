---
id: q-public-reputation-signal
type: question
status: open
date: 2026-10-13
title: 公開の評判（取得元の公開の評価・クチコミ）を推薦に使えるか
links:
  - depends_on: catalog-terms-no-redistribution
  - depends_on: dec-polite-crawling
  - affects: comp-recommender
---
映画のデータでは作品の評判が人物の手がかりよりずっと強かった（eval-douban-consensus-strong）。たぐりで使うなら、取得元が公開している評価・クチコミの量と、利用規約・取得の作法（catalog-terms-no-redistribution・dec-polite-crawling）を確かめる必要がある。過去の調べで、クチコミの材料量を測るスクリプト（measure_net_d.py）がある。
