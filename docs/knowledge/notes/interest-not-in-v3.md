---
id: interest-not-in-v3
type: finding
status: confirmed
date: 2026-10-14
title: いまの推薦（person-ordinal-v3、Worker）は「興味あり」を材料に使っていない。前の版（recommend2）は 2026-08-26 の指示で重み 0.5 の正例として名簿に入れていたが、v3 に移したときに持ち越していない
sources:
  - cloudflare/src/recommend.js
  - cloudflare/src/screens/recommend.js
  - tools/review/measure_nets.py
  - tools/review/recommend2.py
  - tools/review/user_recommender.py
links:
  - affects: impl-person-ordinal-v3
  - depends_on: lit-implicit-confidence
  - depends_on: impl-favourite-seed
---
起案者の問い（2026-10-14）「過去の観劇記録じゃなくて開幕リマインドから興味ありを選んだ段階でも出せるんじゃないの？なんで過去だけに絞っているのか」。コードで確かめたこと:
- Worker の推薦（recommend.js scoreFromIndex）が読むのは、評価を付けた記録（rated）と、お気に入りから作る仮の ◎（seeds、z = 0.4√12・重み 3/(3+評価の数)）だけ。reaction の興味あり（interest=1）は、答えた公演をおすすめから外す（screens/recommend.js 101 行目）のと、件数の表示・理由の作品名にしか使っていない
- 前の版 recommend2 は、起案者の指示（2026-08-26「観ればよかったで挙がった人名は興味ありと同じ扱いにして推薦に反映させて」）で、興味あり・観ればよかったの公演の作り手を ◎ より弱い正例（INTEREST_W = 0.5）として名簿に足していた（measure_nets.add_interest_roster）。v3 に移すとき、この橋は作り直していない。意図して外したという記録は見つからない
- v3 は評価を本人の中の順位（z）で読むので、興味ありをそのまま「評価」に混ぜることはできない（反対向きの信号が無く、全部同じ値なら z が 0 になる）。ただし、お気に入りと同じ「仮の ◎」の口（seeds）に入れれば入る
- 分からないこと: 重みをいくつにすれば当たりが良くなるか（0.5 も AUC で測った値ではない）。開幕リマインドの公演は一覧（catalogue）にしかないものがあり、その人物は索引（rec_people）から引けない
