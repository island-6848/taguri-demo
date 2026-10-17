---
id: dec-ui-1018b
type: decision
status: adopted
date: 2026-10-18
title: 理由は畳まない・購入済みでもカードを残す・同じ公演の重複を直す・日記帳をノートの見た目に・行に公式サイト・ロゴ案 3 つ
sources:
  - web/app.js
  - web/theme.css
  - cloudflare/src/screens/recommend.js
  - cloudflare/src/screens/reminder.js
  - cloudflare/src/screens/rowinfo.js
  - cloudflare/src/screens/autolink.js
  - cloudflare/test/same-production.test.js
  - docs/design/logo/sheet.html
links:
  - depends_on: dec-rec-row-like-card
---
起案者の指示（2026-10-18）。
- おすすめ理由は本数に関わらず全部出す（3 本を超えた分を畳む仕組みを外した）
- 回答の押し口: 枠線を 2px → 1.5px、押し口どうしの隙間を 10px → 6px
- 購入済みを押しても、どの画面でもカードを消さない。帯の下に「購入済みにしました。購入済み公演を見る」を添える（以前は一覧から外して 1 行を残していた）
- **同じ公演が 2 枚出る**（コードを読んで見つけた原因。本番の D1 では確かめていない）:
  - おすすめ: 束の鍵（rec_stage.tour）は題名・団体・作り手の全部から作るので、会場ごとの出演の行の違いなどで同じ公演が別の束になる → 題名の鍵（tkey）と団体の鍵（gkey）が同じ束を 1 つにまとめ、会場も合わせる（sameProduction。版 screen-v18 で控えを作り直す）
  - おすすめの入れ替え: 画面に出ている番号だけで比べていた。束の代表の会場は答えるたびの並べ直しで変わるので、同じ公演が別の番号で足された → 束のどの会場の番号でも出ていれば足さない。続けて 2 枚に答えたときの重なりは画面側でも止める
  - 開幕リマインド: 索引と一覧の同じ公演を合わせる鍵に終わりの日が入っており、一覧の行は終わりの日が無いと合わなかった → 会場（表記ゆれを寄せる）・初日・題名で合わせる。県の分からない行は、同じ題名が 1 つの地方にだけあればその束へ。絞った一覧に出ている公演は「都道府県が分からない公演」の箱に重ねない
- 評価一覧・日記帳の行: 過去の公演（past_stage）の団体と県も読み、主催を人の絵記号で出す。ポスターの下に「公式サイト」（公演の欄の URL）、無ければ「公演ページ」（stage.corich.jp。stage_id はその番号）
- 日記帳はノートの見た目: 生成りの紙・横罫・綴じ穴・余白の赤い縦線・重ねたページの影。画面の [data-route] で日記帳だけに当てる
- ロゴ案 3 つ（docs/design/logo/）: A 糸玉の幕（推し）・B 半券と糸・C 判子。字は Zen Maru Gothic Bold。決めるのは起案者
