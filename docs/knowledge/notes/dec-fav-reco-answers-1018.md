---
id: dec-fav-reco-answers-1018
type: decision
status: adopted
date: 2026-10-18
title: 起案者の答え（2026-10-18）: お気に入りがあるのに 0 件なら一文添える（C）、作曲・音楽も広げる元に入れる、ハッシュタグ一覧はこれからの公演のみ、▸ はそのまま、サイドバー・パンくずを見出しに合わせる、興味ありの並べ替えを月のタブの下へ
sources:
  - cloudflare/src/screens/recommend.js
  - cloudflare/src/recommend.js
  - tools/review/user_recommender.py
  - cloudflare/src/screens/lists.js
  - cloudflare/src/screens/index.js
  - cloudflare/src/screens/cards.js
  - web/app.js
  - cloudflare/test/fav-reco.test.js
  - cloudflare/test/recommend-screen.test.js
links:
  - answers: q-fav-reco-running-shows
  - depends_on: fix-fav-only-no-reco
  - depends_on: dec-fav-spread-roles
---
起案者の答え「1.C。2.入れて。3.ハッシュタグ一覧はこれからの公演のみで可。4は今ので良い。5.合わせて。6.お願い。」（2026-10-18）。

1. 〔q-fav-reco-running-shows〕は C。お気に入りを登録しているのにおすすめが 0 件のときだけ、案内の上に「お気に入りに登録した名前と関わりのある人の、これから観られる公演はまだ見つかっていません。…」の一文（`p.rcount.favnone`）を出す。候補を「まだ始まっていない公演」に限る約束は変えない。
2. お気に入りの公演から広げる役職に 作曲・音楽・音楽監督・編曲 を足す（重み 0.1、美術などと同じ。〔dec-fav-spread-roles〕の続き）。Python の user_recommender も同じ。rec_cache は screen-v34。
3. ハッシュタグの一覧（/recommend/tag）は、これからの公演だけのまま。
4. 折りたたみの小さな三角はそのまま。
5. サイドバー・メニュー・パンくず・画面の名前を見出しに合わせた: 「今週のあなたへのおすすめ」「購入済の公演」。画面の中で行き先を指す文（購入済みの印の道、トースト、興味ありの説明）も「購入済の公演」にした。古い Python の review の画面（tools/taguri/app.py）は変えていない。
6. 「興味あり」の公演の並べ替えを、月のタブの下に移した。

確かめたこと: JS 448 件・Python の試験は通る。e2e は 52 中 49。落ちる 3 件（公演カレンダー: 行く日を 2 つ、観察: 行く日が過ぎた券、Ctrl+クリック）は、変えていない master でも 10/19（JST）以降は落ちる。fixture の日付が 2026-10-18 前後で固定されているためで、今回の変更とは関係ない。
