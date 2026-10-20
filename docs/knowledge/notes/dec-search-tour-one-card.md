---
id: dec-search-tour-one-card
type: decision
status: adopted
date: 2026-10-20
title: 探すの「今後の公演」（前の「これから観られる公演」）は、ツアーを 1 枚にまとめ、答えは全会場に付ける
sources:
  - cloudflare/src/screens/search.js
  - cloudflare/src/screens/entity.js
  - cloudflare/test/search-uncarded.test.js
links:
  - affects: comp-cf-worker
---
起案者の指示（2026-10-20）「検索から『これからの公演』を出すとき、ツアーがバラバラに出ていて、バラバラに興味ありを押せるようになってしまってる。まとめて。『今後の公演』に名前変えて」。

- search.upcomingHits: 当たった公演を、索引の同じ tour（rec_stage.tour。おすすめと同じ束ね方）でまとめる。索引に無い新しい公演（catalogue だけ）は題名の鍵と団体で束ねる。並びの先頭（いちばん早い会場）を代表のカードにし、ほかの会場は日程の会場ごとの行に出す
- カードの data-tours にほかの会場の番号を入れる。押した答えは、おすすめと同じく全会場に付く（reactAction の siblings）。答えの印・興味ありの形も、どの会場に付いていてもそのツアーのものとして出す
- 件数・ページ送り（5 件ずつ）は公演（ツアー）の数で数える。月のカレンダーの数は前のまま会場ごと
- 見出しと札の名前を「今後の公演」にした（探す・人物のページ）。お気に入り・設定・おすすめの説明文の「これから観られる公演」はそのまま
