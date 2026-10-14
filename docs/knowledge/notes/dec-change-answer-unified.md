---
id: dec-change-answer-unified
type: decision
status: adopted
date: 2026-10-14
title: 答えた公演（興味あり・興味なし・持っている）は、どの画面でも「回答を直す」1 つにし、押すと三択が開く
sources:
  - cloudflare/src/screens/cards.js
  - cloudflare/src/screens/reminder.js
  - cloudflare/scripts/build_cards.py
  - tools/review/render_recommend.py
  - tools/taguri/digest.py
  - web/app.js
  - cloudflare/test/lists-screen.test.js
  - tools/taguri/test_digest.py
links:
  - depends_on: lit-nielsen-heuristics
---
起案者の指示（2026-10-14）「一度興味ありなしなどの回答を押したものに関しては、おすすめに出すときも『回答を直す』に統一すればいいのでは」。
- それまで: 興味ありの一覧は「回答を変える」、開幕リマインドの答えた行と購入済み公演は押し口なし（直せなかった）、おすすめは答えた公演を出さない
- 変えた: 興味あり・購入済み公演のカードと、開幕リマインドの「興味あり」「興味なし」「持っている」の行に「回答を直す」を置き、押すと隠してある三択が開く（cards.changeAnswer、app.js の data-btns-open をカードとリマインドの行の両方で効かせた）。Python 版（build_cards・render_recommend・digest）も同じにし、一致テストを保つ
- 2026-08-26 の指示「すでに興味ありとか評価してる公演には『興味あり』などのボタンを表示しないで」は守る（三択は押すまで隠れている）
- おすすめは今も答えた公演を出さない（答えると下の一覧に移る）。説明文の「下にまとめてあります」は実際に無かったので、「『興味あり』『購入済み公演』などに移します」に直した
- お気に入りは読むだけのまま（未回答の公演にも押し口が無い）。変えるかは未定
