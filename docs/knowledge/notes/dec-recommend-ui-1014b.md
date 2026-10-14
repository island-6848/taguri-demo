---
id: dec-recommend-ui-1014b
type: decision
status: adopted
date: 2026-10-14
title: おすすめの見直し（2026-10-14 の 2 回目）── 料金はつまみ・絞り込み 3 つを横 1 列・ページの地図・ツアー日程を常に・感想のハッシュタグ・券の案内へ #tickets・記録を速く・券からお気に入りに
sources:
  - web/app.js
  - web/theme.css
  - tools/taguri/app.py
  - tools/taguri/serve.py
  - tools/taguri/hashtags.py
  - tools/review/render_recommend.py
  - cloudflare/src/screens/hashtags.js
  - cloudflare/src/screens/rate.js
  - cloudflare/test/screens/scenarios.json
links:
  - depends_on: react-slow-cause
  - affects: dec-recommend-ui-1014
  - affects: dec-ticket-price-filter
  - affects: dec-phone-nav-four
---
起案者の指示（2026-10-14）をまとめて入れた。
- **料金はつまみ**（選択肢をやめた）。1,000 円〜15,000 円まで・上限なしの 12 段。動かしたその場で券を隠す（サーバーに送らない）
- **絞り込みは横 1 列:** 場所・効かせ方・料金の 3 つを札にして 1 行に並べ、押した 1 つだけを下に全幅で開く（app.js の filterRow。中身はそれぞれの details のまま）
- **ページの地図:** おすすめ＝選ぶ（今週のおすすめ・興味あり・お気に入り）、予定＝日を確かめる（公演カレンダー・開幕リマインド・購入済み公演）。開幕リマインドを予定へ移した。URL は変えていない。パソコンの左の帯も「予定」の組にした
- **子が 3 つのすだれは 1 行**（スマホ）
- **ツアー日程は券に常に全部出す**（「日程」の行。日程の順に並べ、このおすすめの会場に札。県で絞り込んでいても全会場）
- **感想のハッシュタグ:** 感想に `#タグ` と書けばタグになる（`hashtags.py`、Worker は `screens/hashtags.js` で同じ出力）。感想の画面にタグの一覧（多い順）と、押したタグの感想の一覧（新しい順・`/rate/notes?tag=`）。書いてある感想の中のタグはリンクに、感想を書く欄の上には使ったタグの札
- **発売の札 → 公式サイトの `#tickets`:** 起案者の知見「大体チケットってページか、#tickets をつけたアンカーリンクのとこにある」から、公式サイトの URL に `#tickets:~:text=チケット` を付ける（その場所があればそこへ、対応するブラウザはページの中の最初の「チケット」へ）。ページは読みに行かない
- **記録を速く:** react-slow-cause のとおり、記録と入れ替わりの 1 枚を別の要求に分けた
- **券からお気に入りに:** 公演名の右の ☆ で、その券の作品・団体・出演・作り手の名前を並べ、押した名前を登録（/api/favourite）
