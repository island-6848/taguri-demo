---
id: dec-recommend-worker-cards
type: decision
status: adopted
date: 2026-10-14
title: おすすめの画面を Worker に移す。カードは毎日の取得で Python の ticket() が作り置き（rec_card）、Worker は順位・理由・ポスターだけを差し込む
sources:
  - cloudflare/scripts/build_cards.py
  - cloudflare/migrations/0017.sql
  - cloudflare/src/screens/recommend.js
  - cloudflare/scripts/deliver_catalogue.py
  - cloudflare/test/recommend-screen.test.js
  - cloudflare/test/test_build_cards.py
  - https://github.com/island-6848/taguri-crawler/commit/214d3c6
links:
  - depends_on: dec-native-cutover-now
  - affects: comp-native-screens
  - affects: dec-free-tier-only
---
起案者の指示（2026-10-14）「おすすめの画面を移して」。
決めたこと:
- **カードは移植しない。** render_recommend.ticket（約 600 行の部品）を JS に書き直すと見た目がずれる。カードのうち公演だけで決まる部分（題名・日程・ツアー全日程・料金・発売・出演者・あらすじ・三択・理由の欄）は、毎日の取得で Python の ticket() そのもので作り、D1 の rec_card（migration 0017、版つき。rec_meta 'rec_card'）に入れる（build_cards.py、deliver_catalogue.py の段、cards-upload.sql）。利用者ごとに違う 3 か所（耳の番号・おすすめ理由・ポスター）だけ印（<!--rank--> <!--why--> <!--poster-->）にし、Worker が埋める。埋めた結果が RR.card と同じになることを test_build_cards.py が確かめる
- **順位は Worker の推薦（src/recommend.js、Python と一致を確かめ済み）。** 材料は移した画面が書く works（評価・結び付けた公演）・favourites・reaction。三択に答えた公演は外す。ツアーは 1 枠（rec_stage.tour）。上位 400 作品と各会場の県を rec_cache に置き、評価・反応・お気に入りが変わるか日付・索引が変わるまで使い回す
- **理由の行**は reason_rows の人物（上位 4、作品名つき）と種類（#形式など、上位 2）。お気に入りの「申告」の行・感想による並べ替え・出さない語はまだ
- **県の絞り込み**（pref_form、?f=1 で app_setting に保存）は移した。地図（prefmap.panel）と効かせ方（weight_form）はまだ
- **三択（/api/react）**: reaction 表に書く（押し直しで前の列を消さない）。同じ作品の他会場（カードの data-tours）にも同じ答え。理由だけの更新も受ける。fill_only で次の 1 枚を返す
無料枠: rec_card は 1 日に「これからの公演の数 × 2 行」（入れる・古い版を消す）を書く。カードの日付が今日基準なので、ほぼ毎日新しい版になる。書く前に deliver_catalogue の予算（今日の残り）と比べ、越えるなら入れずに飛ばす。1 枚は約 4〜5 KB。画面を開くたびの読みは、使い回しが効けば数十行（rec_card 15 行・poster・数える問い合わせ）。
