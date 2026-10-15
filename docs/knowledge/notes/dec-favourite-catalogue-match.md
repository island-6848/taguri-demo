---
id: dec-favourite-catalogue-match
type: decision
status: adopted
date: 2026-10-14
title: お気に入りの名前は、作り置きのカードだけでなく、集めた公演一覧（catalogue）全体からその場で探す
sources:
  - cloudflare/src/screens/lists.js
  - cloudflare/src/screens/fallback.js
  - cloudflare/test/lists-screen.test.js
links:
  - answers: q-name-search-without-corich-search
  - depends_on: corich-search-waf-403
---
起案者の指示（2026-10-14）「『お気に入り』に一個追加した時点でその情報を取りにいってほしい」→「たぐりが集めている公演から出してよ勿論。一覧になかった場合だけ取りに行って（その際数分かかるのはしょうがない）」。
- お気に入りの画面は、作り置きのカード（rec_card）に加えて、毎日届ける公演一覧（catalogue、CoRich のサイトマップとステイジーズカレンダーから集めたもの）を、登録名の先頭 2 文字で絞ってから正規化した文（団体・題名・劇場・クレジット・あらすじ・題材）で照合する（catalogueMatching）。カードの無い公演は fallback.js の簡単なカードで出し、「登録した〇〇の公演です」を付ける
- catalogue の走査はこれからの公演を全部読むので、お気に入りの画面だけで行う（興味あり・開幕リマインドなどの振り分けは今までどおりカードだけ）
- 一覧に無い名前を外へ取りにいく経路は無い：CoRich の名前検索はデータセンターからの接続を 403 で断る（corich-search-waf-403）。接続元を変えてすり抜けない（dec-polite-crawling）。集めた一覧はサイトマップ経由で CoRich に載る公演を毎日集めているので、載れば翌日の更新のあとに出る。そのことを空のときの案内に書く
- 残り：団体の公式サイトを直接見る経路（URL をどう知るか）

2026-10-15 の直し（起案者の指摘「お気に入りで「上村聡」を登録したら、「上村聡史」まで拾っちゃってる」）: 人で登録した名前は、本文の文字列の一部ではなく、名前全体で当てる。本文の文字列（blob）は空白を詰めてあり、名前の切れ目が分からない。そこで、当たった公演の出演・スタッフ欄を credits.parseCredits で名前ごとに切り、登録した名前と同じ名前があるときだけ残す（lists.wholePersonNames）。欄を読めない公演はこれまでどおり文字列で当てる。団体・主催・作品・原作者・題材の当て方は変えていない。おすすめから外す判定・開幕リマインドのお気に入りも同じ nameHits を通るので、同じく直る。
