---
id: q-split-pieces-1019
type: question
status: open
date: 2026-10-19
title: 1 公演に複数の作品がある記録を、利用者が望んだときだけ作品ごとに分けて評価・推薦・感想・題材の読み取りをするか。分けた作品の重みと出演者の割り当てをどうするか
sources:
  - https://github.com/island-6848/taguri-demo/blob/master/cloudflare/src/screens/recommend.js
  - https://github.com/island-6848/taguri-demo/blob/master/cloudflare/src/recommend.js
  - https://github.com/island-6848/taguri-demo/blob/master/tools/credits/extract_theme_llm.py
  - https://github.com/island-6848/taguri-demo/blob/master/tools/credits/fetch_credits.py
links:
  - depends_on: f-multi-piece-handling-1019
---
起案者の問い（2026-10-19）「1 公演を 1 件として表示しつつ、評価や推薦、感想やあらすじの抽出の仕組みなどは作品数分（チェーホフのオムニバスなら 6 本とか）分けられる？ただしユーザーが分けたいとしたときの任意」。

コードから分かったこと（2026-10-19、master）:
- 評価は works の 1 行に 1 つ。推薦は ratedWorks（screens/recommend.js:125）→ independentRatings（recommend.js:159、結び付けた公演ごとに 1 評価）→ personValues（recommend.js:311、評価の z を公演の全員と #題材 に足す）
- 公演の出演・スタッフ（rec_people・past_stage.people）は作品ごとの区切りを持たない（fetch_credits.parse_stage・measure_nets.parse_credits は平らな並び）
- 題材の読み取り（extract_theme_llm）は公演（stage_id）か記録（work_key）ごとに 1 回

案（未決）: 子の表 work_piece を足し、分けた記録は作品ごとに評価・気になった所・感想・出演者の絞り込みを持つ。推薦は作品ごとの評価を 1/n の重みで足す（分けても 1 公演の影響は増えない）か、1 本ずつ満額か。作品ごとの出演者は利用者が選ぶ（cast_off と同じ画面）。題材は、あらすじが作品ごとに書いてあるときだけ作品ごとに読み、無ければ公演全体のまま。
