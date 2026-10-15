---
id: dec-credit-part-names
type: decision
status: adopted
date: 2026-10-15
title: 出演欄の「役名：名前」「アンサンブル：名前」は、コロンの後ろだけを名前として読む（Python の measure_nets._names と Worker の credits.names を同時に）
sources:
  - tools/review/measure_nets.py
  - cloudflare/src/screens/credits.js
  - cloudflare/test/credits.test.js
links:
  - answers: q-credit-part-names
---
起案者の指示（2026-10-15）「直して」。parseCredits({出演: 'ジャン・バルジャン：福井晶一／吉原光夫\nジャベール:川口竜也\nアンサンブル：田中、高橋次郎'}) が、福井晶一・吉原光夫・川口竜也・田中・高橋次郎 を返すようになった。Python と Worker の一致試験（credits.test.js）にこの書き方を足した。tools/review/test_measure_nets.py は直す前から 1 件失敗していて、件数は変わらない。
- 効き始め: 推薦の索引（rec_people・rec_credit）は取得のたびに Python で作り直すので次の Catalog から。過去の公演（past_stage）は読み直した公演から。手で入れた出演者はすぐ
