---
id: dec-search-middot
type: decision
status: adopted
date: 2026-10-24
title: 探すは中黒などの点（・ ･ · • ‧ ∙）を除いて比べる。ミス・サイゴンを「ミスサイゴン」と打っても当たり、点を入れて打っても点の無い題名に当たる
sources:
  - cloudflare/src/screens/search.js
  - cloudflare/test/search-middot.test.js
links:
  - affects: dec-search-bar-emphasis
---
起案者の指示（2026-10-24）「正式名称はミス・サイゴンだけど点を含む作品名は、ミスサイゴンのように点を除いても検索にヒットするようにして」。

分かったこと（コードと試験）:
- 題名の鍵（stage-search.titleKey・works.titleKey）は前から「・」を除いている。過去の公演（tkey の先頭一致）と、観劇記録の追加の候補はもともと当たっていた
- 当たらなかったのは探すの「今後の公演」。索引（rec_stage・rec_card）と一覧（catalogue）を、打った言葉そのままの部分一致（SQL の instr）で引いていた。「ミスサイゴン」は「ミス・サイゴン」の一部ではないので 0 件だった。当たった所を書く JS の比べ方（norm）も同じ

直し方:
- search.js の fold（JS）と sqlFold（SQL）の両方で、点を除いてから比べる（波ダッシュをそろえるのと同じ所）。打った言葉と本文の両方から除くので、点を入れて打っても当たる。題名・団体・出演者の名前（「チェウヒョク」で「チェ・ウヒョク」）・題材・劇場のどれでも同じ
- 人の索引（pastFromIndex）は名前の完全一致で引くので、点を除いた形と、打ったままの形の両方で引く（前から 2 通り引いていた）

確かめたこと: search-middot.test.js（索引・一覧・過去の公演・観た記録・出演者の名前・観劇記録の追加の候補・点を入れて打った場合）。npm test が通る。

無料枠: 読む行は変わらない（SQL の比べ方に replace が 3 つ増えるだけ）。
