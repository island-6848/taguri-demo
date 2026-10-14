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
