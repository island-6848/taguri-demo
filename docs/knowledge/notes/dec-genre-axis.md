---
id: dec-genre-axis
type: decision
status: adopted
date: 2026-10-16
title: 大きなくくりのジャンル（#ジャンル: 2.5次元・宝塚）をおすすめ理由に出し、理由の ✕ で外すとその公演ごとおすすめから外す
sources:
  - tools/review/user_recommender.py
  - cloudflare/scripts/build_recommend_index.py
  - cloudflare/src/recommend.js
  - cloudflare/src/screens/recommend.js
  - cloudflare/src/screens/lists.js
  - https://gikyokutosyokan.com/blog/ja/2026-musical-vs-straight-play
  - https://www.oricon.co.jp/news/2317972/full/
links:
  - depends_on: genre-25d-signals
  - depends_on: impl-kind-reason-off
  - affects: comp-recommender
---
起案者の指示（2026-10-16）:
- 「おすすめ理由に2.5次元として出してほしい。で、いらない人はそれ✕押せばいいから」
- 「宝塚は宝塚ってジャンルかな」

印の付け方（user_recommender.genres）:
- 宝塚: 主催・劇団が宝塚歌劇団のとき。漫画が原作でも宝塚とする。スタッフ欄に宝塚歌劇団とあるだけの公演（衣裳を貸しているなど）は入れない。
- 2.5次元: 次のどちらかのとき。
  - 原作の書き添えが漫画・アニメ・ゲーム原作。
  - 主催が「〜製作委員会」で、題名が『作品名』や THE STAGE の型か、題名のかぎ括弧の作品名が製作委員会の名前にもある。
- 2026-10-16 のこれからの公演では、2.5次元 18 作品、宝塚 7 作品。
- SPY×FAMILY・セーラームーンなど、原作の欄も製作委員会も無いものは漏れる。

理由と ✕:
- #ジャンル は公演の中身の種類（CONTENT_AXES）として理由に出す。出典は「原作のクレジットと主催」。
- ほかの種類の ✕ は理由から外すだけで、公演は消さない（impl-kind-reason-off）。ジャンルの ✕ は、その印の付いた公演をおすすめに出さない。
  - 外した公演は、索引（rec_credit）を 1 回読んで引く。
  - お気に入りの画面の「使わない理由」から ✕ で戻せる。
- 本番では、次の索引の配信で #ジャンル の行が入ってから効く。

起案者の大枠（ストレートプレイ・ミュージカル・2.5次元・宝塚）の裏付け:
- ストレートプレイとミュージカルを演劇の 2 つの基本の分け方とする解説がある（戯曲図書館）。
- 販売サイトのローソンチケットは、ストレートプレイ・ミュージカル・2.5次元・宝塚歌劇・小劇場などを並べた区分を使っている（検索結果の要約で見た範囲）。
- ぴあ総研の白書は、2.5次元ミュージカルの市場を別に集計している。
- 学術的に定まった体系は見つからない（genre-schemes-found）。
- 2.5次元は原作の出どころによる呼び名で、形式（ミュージカルかストレートプレイか）とは別の軸になる。そのため 2.5次元のミュージカルは「ミュージカル」とも重なる。
