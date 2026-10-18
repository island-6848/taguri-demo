---
id: dec-font-accent-five
type: decision
status: superseded
date: 2026-10-18
title: 書体は Zen角ゴシック New が基本。さわらびゴシックは指定した 5 か所（公式サイト・発売の状況・お気に入りの名前の札・理由の人物/種類・評価しない）とロゴだけ
sources:
  - web/fonts.css
  - cloudflare/test/fonts.test.js
  - tools/review/render_recommend.py
  - cloudflare/src/screens/grade.js
links:
  - supersedes: dec-font-sawarabi-round
---
起案者「今って本文はzen角ゴシックだよね？指定した箇所だけ丸ゴシックにして。公式サイトのボタン、発売済みなどのボタン、お気に入り登録したときのタグ、おすすめ理由に出てくる種類とか人物とかの文字、評価しないのボタン」（2026-10-18）。同じ日に「丸ゴシックはさわらびゴシックでいいや」と言っているので、ここでの「丸ゴシック」はさわらびゴシックとした。

決めたこと（web/fonts.css の `--font-accent`）:
- さわらびゴシック（400、作り太りなし）: `.sitebtn`（公式サイト）、`.sale .pill`（発売の状況の札。render_recommend.py の sale_pill が作る「発売済み」「確認できず」など）、`.ftag`（お気に入りに登録した名前の札。中のリンクと ✕ も）、`.rs .net`（おすすめ理由の「人物」「種類」）、`.rb button.nograde`（評価しない。grade.js）
- ほかのボタン・両端が丸い押し口と札は Zen角ゴシック New に戻した。形を見て印を付ける round-text.js は要らなくなったので外した（どの頁も読まない）
- 公演名は Zen角ゴシック New（太字）のまま。ロゴの「たぐり」はさわらびゴシックの字形のまま（指定は文字の表示についてで、ロゴは図形のため変えていない）

確かめたこと: 部品を並べた頁で計算後の書体（5 か所と中の字だけがさわらびゴシック、ほかのボタン・「戻る」・丸い札・公演名・題字は角ゴシック、判子は明朝）。JS 389 件（fonts.test.js で、さわらびゴシックの指定が 5 か所の 1 つの規則だけにあること）、e2e-walk 41 段。
