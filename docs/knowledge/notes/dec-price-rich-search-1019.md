---
id: dec-price-rich-search-1019
type: decision
status: adopted
date: 2026-10-19
title: 価格帯は閉じて「min円～max円」（同じなら 1 つ）、開いて券種ごと高い順、座席の決まり（全席指定など）は必ず出す。あらすじは管理画面で書式つき（寄せ・大きさ・書体・太字）で入れられる。探すの過去の公演は見つかった分を全部出す
sources:
  - web/app.js
  - web/theme.css
  - cloudflare/src/screens/override.js
  - cloudflare/src/screens/search.js
  - tools/admin/admin.html
  - tools/admin/admin.py
  - cloudflare/test/rich-synopsis.test.js
  - cloudflare/test/title-leads.test.js
  - cloudflare/test/test_admin_tool.py
  - cloudflare/test/e2e-walk.js
links:
  - depends_on: dec-ui-1019
---
起案者の指示（2026-10-19）:
「価格帯の表示を修正して。折りたたむ前は『min円～max円』（min=maxならばmax円）。展開したら『S席 max円 / A席 min円』・・・などの表示。あと座席に『指定』とか『自由』が書いてあるならそれも必ず明記してほしい」
「あらすじ、凝ってるものはそのまま入力できるようにしたい（中央寄せとか、書体変更のやつたまにある）管理者画面でその辺の書体管理したまま入力できる欄に変えて」
「検索結果、新しい順から15件表示するのではなく、ちゃんと全件表示して」

決めたこと:
- 価格帯（app.js priceSummary）: 閉じた 1 行は明細の金額のいちばん安い〜いちばん高い（同じなら 1 つ）。料金の欄に座席の決まり（全席指定・全席自由・指定席・自由席・日時指定・整理番号付自由・立見）があれば閉じた行の後ろに添える。開くと券種ごとの行を高い順。座席の決まりが券種の名前に無ければ「S席(指定)」と添える。券種が 1 つで閉じた行と同じなら開く中身は無い。会場ごとに料金が違うカード（日程の表に料金がある）はこれまでどおり。
- 書式つきのあらすじ: 管理画面の欄を書式の効く入力欄（contenteditable）にし、太字・斜体・下線・左/中央/右寄せ・小さく/大きく・明朝/ゴシック・書式を消す、の押し口を付けた。書式ごと貼り付けたものも、許した形に直して入れる。本番の CSP は style 属性を許さない（style-src 'self'）ので、寄せ・大きさ・書体は決まった class（ta-left/center/right・fs-s/l・ff-mincho/gothic）で持ち、頭に <!--rich--> を付けて stage_override.synopsis に置く。本番の Worker（override.richHtml）が許した札（p br div span b strong i em u s small）と class だけに絞り直して出す（script・style 属性・リンク・画像は落ちる）。カードでは書式を保ったまま高さで畳み、はみ出すときだけ「続きを読む」。題材の読み取り（Claude Code）・検索などには文字だけを渡す（admin.plain_synopsis・override.richText）。書式の無い入力は、これまでどおり文だけで保存する。
- 探すの過去の公演: 見つかった分を全部出す（前は新しい順に 15 件）。題名で引く行は 1 回の検索で 600 行まで（短い言葉で何千行も読まないため。D1 の読み取りの無料枠）。越えたときはそう書く。これから観られる公演（カード）は、これまでどおり上演日の近い 8 件と残りの件数（カードを何十枚も作ると Worker の CPU の無料枠を越えるおそれがあるため。変えるなら起案者に確かめる）。

確かめたこと: 単体の試験（JS・Python）。e2e の段「探すのカード: 価格帯の幅と券種・書式つきのあらすじ」（閉じた行「6,000円～12,000円」、開いて S席 12,000円 / A席 8,000円 / U-25 6,000円、中央寄せと明朝が効き script が残らない）と、電話の幅の写し。管理画面の欄は Chromium で、貼り付けた書式（style の text-align・font-family・font の size・h2）が決まった class に置き換わることを確かめた。管理画面を本物の D1 につないだ保存までは試していない。
