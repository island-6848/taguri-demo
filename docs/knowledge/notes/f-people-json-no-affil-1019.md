---
id: f-people-json-no-affil-1019
type: finding
status: confirmed
date: 2026-10-19
title: 推薦の索引の出演者（rec_people・past_stage の people、rec_stage.credits）は、名前の後ろの（所属）を外した名前だけ。所属は別の表 rec_affil。書かれたままの文は公演の欄（entry.fields）に残る
sources:
  - https://github.com/island-6848/taguri-demo/blob/master/tools/review/measure_nets.py
  - https://github.com/island-6848/taguri-demo/blob/master/cloudflare/src/screens/credits.js
  - https://github.com/island-6848/taguri-demo/blob/master/cloudflare/migrations/0039.sql
  - https://github.com/island-6848/taguri-demo/blob/master/cloudflare/scripts/build_recommend_index.py
links:
  - affects: dec-split-pieces
---
起案者の問い（2026-10-19）「json の出演者に（劇団名）とか含めてる？」に、master のコードを読んで答えた。

- measure_nets._names は、区切りで割る前に括弧（全角・半角）を _PAREN で外す（「鎌塚慎平(劇団・木製ボイジャー14号)」が割れないように）。姓名の間の空白も詰める。parse_credits → build_recommend_index が rec_people・rec_stage.credits・past_stage.people に入れるのはこの名前
- Worker の手入力の出演者（screens/credits.js）も同じ PAREN で外す。作品ごとの出演者（work_piece.cast_in）は rec_people の名前から選ぶので、括弧は付かない
- 所属は measure_nets.affiliations が「名前（所属）」の括弧を読み、rec_affil（0039）に 1 公演 1 行で入れる。Wキャスト・日付・楽器・客演などの注記は所属として拾わない。「A・B（劇団X）」はどちらの所属か決められないので拾わない
- 画面に出す公演の欄（rec_stage.entry の fields、catalogue.metadata）は取得元に書かれたままで、括弧も残る

分からなかったこと: 閉じていない括弧（「俳優（劇団X」）や入れ子の括弧が、名前に残る件数（手元に取得データが無く数えていない）。
