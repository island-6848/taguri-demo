---
id: dec-diary-collage-quiet
type: decision
status: adopted
date: 2026-10-18
title: 日記帳のコラージュは控えめに。色はテーマのパレットだけ、テープは形を 4 種類、「劇」の切手は外す
sources:
  - web/theme.css
  - web/app.js
  - cloudflare/test/e2e-walk.js
links:
  - supersedes: dec-diary-collage
  - depends_on: dec-rec-row-like-card
---
起案者の指示（2026-10-18）「日記帳のデザインがポップすぎて浮いてる。あくまでこのサイトはスタイリッシュとシンプルの中間を保ったデザインにしたい。色も勝手に増やさず、テーマにあるカラパレから使って。テープは柄だけでなく形自体（うねうね、四角、丸シールなど）も何種類かほしい。右上にある『劇』も不要。」を受けて、同じ日の dec-diary-collage を置き換えた。

引き継いだもの: 日付の形 2026/10/17(土)（row.js の fullDate と Python の full_date）、方眼の紙・綴じ穴・白い縁のポスターと少しの傾き、テープの中心をポスターの上辺に重ねる置き方、破った紙のあらすじ、感想の欄の地の色と「ここに感想を書けます」の案内、地を押すと書き始められる処理（app.js）。

変えたこと（web/theme.css の日記帳の塊）:
- 日記帳の塊では、新しい色の値（16 進・色の名前）を使わない。--plane・--surf・--ink・--ink2・--mute・--ring・--base・--curtain・--sel・--sel-curtain・--warn と、それを color-mix で薄めたものだけを使う。紙の地も --surf と --plane を混ぜて作る（前の版はクリーム色を混ぜていた）。
- 外したもの: 右上の「劇」の切手、蛍光ペンの下線、日付印の傾きと二重枠、色紙の切れ端の 4 色。
- 日付は細い枠（--ring）の小さな札にし、字は --ink2 にした。
- ポスターの後ろの紙は 1 枚だけにし、--plane の地に細い線を付けた。
- テープは形を 4 種類にし、行ごとに順に替える: 細長いマスキングテープ（両端ちぎれ、--base）・四角（--curtain を薄く）・丸いシール（--curtain）・うねうね（上下の縁が波、--ring。mask で切る）。
- 感想の欄は黄色をやめ、--sel を混ぜた薄い地と、--curtain の細い左線にした。
- e2e-walk の「日記帳の見た目」の段は、行ごとに違うことを確かめる対象を、テープの柄から形（幅・高さ・角の丸み・clip-path・mask）に替えた。
