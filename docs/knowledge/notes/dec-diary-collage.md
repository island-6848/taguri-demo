---
id: dec-diary-collage
type: decision
status: superseded
date: 2026-10-18
title: 日記帳はコラージュの見た目にする。日付は yyyy/mm/dd(曜日)、テープはポスターの上辺にかけて 4 柄、感想の欄に地の色
sources:
  - web/theme.css
  - web/app.js
  - cloudflare/src/screens/row.js
  - cloudflare/src/screens/diary.js
  - tools/taguri/app.py
  - cloudflare/test/e2e-walk.js
links:
  - depends_on: dec-rec-row-like-card
---
起案者の指示（2026-10-18）は次の 4 つ。
「日記帳の日付の書き方、yyyy/mm/dd(曜日)で統一して。」
「日記帳ページ、もうちょっとコラージュを意識したデザイン。」
「シール？テープ？がポスターにかかるっていない。ポスターの上辺と、シール？テープ？の中央が重なる位置に配置。テープのデザインも何パターンか用意。」
「『感想』の右に背景色つけて記入欄がここにありますよってわかりやすくして。」

決めたこと（日記帳 /records/works だけ。評価一覧などの行は変えない）:
- 日付は 2026/10/17(土) の 1 続きで出す（月は 2 桁にそろえ、カッコは指示どおり半角）。row.js の recRow に fullDate、Python の _rec_row に full_date を足し、日記帳だけが渡す。HTML は `<span class="dt"><span class="ymd">…</span></span>`。Python 版と Worker の一致テスト（screens.test.js）は両方を同じに直したので、比べ方は変えていない。
- 日付は日付印（幕の色の二重枠、少し傾ける）。題名は蛍光ペンを引いたような下線（text-decoration。行ごとに引ける）。右上に切手（ミシン目の縁、色と傾きは 4 行ごとに替える。字「劇」は読み上げない）。
- ポスター（now printing... も）は白い縁を border で付ける。テープは .pin::before で、中心の高さをポスターの上辺（.pin の上の余白 --pt）に、横の中心をポスターの真ん中（--pl + 縁込みの幅 --pw の半分）に置く。柄は nth-of-type(4n+k) で 無地の和紙（両端をちぎる）・斜めの縞・水玉（両端をちぎる）・格子（ぎざぎざ鋏）の 4 種類。幅・高さ・角度も替える。パソコンの幅では 1.3 倍。
- ポスターの後ろに色紙の切れ端を 1 枚、左下からのぞかせる（.pin::after。色と向きは 4 行ごと）。
- 感想の欄（.inr>.inb）は付箋のような薄い黄色の地と左の線。書いていないときは「ここに感想を書けます」と出す。地のどこを押しても鉛筆と同じに書き始められる（app.js。書いている最中・リンク・文を選んでいるときは何もしない）。
- 色はどれもテーマの変数（--surf・--ink・--curtain・--sel-curtain）から混ぜるので、暗い表示でも沈む。電話の幅（390px）で横にはみ出さない。
- e2e-walk に「日記帳の見た目」の段を足した。日付の形、テープの中心とポスターの上辺のずれ（1.5px 以内）、柄が行ごとに違うこと、感想の欄の地の色、横のはみ出しを、パソコンと電話の幅で確かめ、works-pc.png・works-phone.png を残す。

分かっていないこと: 評価一覧・検索の行の日付（10.17 土 2026 の形）も同じ形にするかは、起案者に聞いていない。

追記（2026-10-18）: 起案者「評価一覧と検索の日付もyyyy/mm/dd(曜日)でそろえて」。row.js の recRow の fullDate と app._rec_row の full_date を既定で true にし、評価一覧・未評価・検索の行も 2026/10/17(土) の 1 続きで出す（日記帳以外の行は .rec-row .dt .ymd の太字だけ。日記帳は日付印の形のまま）。
