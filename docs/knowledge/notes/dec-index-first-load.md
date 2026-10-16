---
id: dec-index-first-load
type: decision
status: adopted
date: 2026-10-16
title: 推薦の索引の初回（約 5.3 万行）は 1 日の書き込みの予算に収まらないので、何日かに分けて入れる。公演ごとにまとめ、開幕の近い公演から
sources:
  - cloudflare/scripts/build_recommend_index.py
  - cloudflare/scripts/deliver_catalogue.py
  - cloudflare/test/test_recommend_index.py
  - cloudflare/test/test_deliver_catalogue.py
links:
  - depends_on: dec-index-diff
  - depends_on: d1-writes-undercounted
---
Catalog #6（run 38816233905、2026-10-15 22:18 UTC〜）の deliver_catalogue の報告（記録の取り込みのセッションが読んだ）: "index": "skipped: 111710 writes would exceed the budget"（差分の初回 53,446 行、rec_stage 4,818 行）、labels 9,616・cards 3,114 は入った、"d1_left_today": 44682。Free-tier の表は D1 の書き込み 57,088/80,000。このままでは毎日 skip され、索引が届かない。
- 直したこと: build_recommend_index.py --max-rows（diff_sql の limit）。変わる行が上限を越えるときは、消す行を先に、次に公演ごと（その公演の rec_stage・rec_credit・rec_people をまとめて）に開幕の近い順で、最後に題名の 2 文字の束（rec_gram）を、上限まで選ぶ。送らなかった行は前のハッシュのままなので、次回の差分にまた出る。途中の日は rec_meta 'index_rev' を「版-left残り行数」にして推薦の控えを捨てさせる
- deliver_catalogue.py: 上限は（予算 − それまでの書き込み − 題名とカードの分 15,000）÷ 3（1 行 2 ＋ rec_stage の索引の分を多めに）。全部入れ終えたときだけ版を控える（途中なら翌日も同じ版の残りを送る）。上限が 0 なら "skipped: no room in today's budget"
- 見込み: 予算 6 万から公演一覧とカードの分を引くと 1 日約 1.4 万行で、初回は 4 日ほど。途中の日も、開幕の近い公演から推薦に使える。過去の公演の投入（past_stage）は残りの予算で動くので、その数日は少なくなる
- 試験: 上限ずつ当てていくと、まるごと入れた表と同じになる。1 日目に入った公演は、その公演の出演・作り手の行がそろっている。開幕の近い公演が先
