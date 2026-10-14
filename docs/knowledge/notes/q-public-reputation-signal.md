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

調べたこと（2026-10-13）: 公開の評判として、取得元（CoRich）の公演ページに「観てきた！」の件数と平均の満足度（★）がある（tools/review/measure_net_d.py・tools/corich/sample_density.py が読み取っている）。ただし (1) 推薦するのはこれからの公演なので、上演前にはクチコミがまだ無い。劇団や作り手の過去の公演の評判を代わりに使う形になる。(2) 公演あたり何件付いているかは、測るスクリプトはあるが結果が記録に無い。(3) 取得元の利用規約の第 6 条 4 項（再配布の禁止）との関係を確かめていない（catalog-terms-no-redistribution）。(4) この作業環境からは取得元を読めない。
