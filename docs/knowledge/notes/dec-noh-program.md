---
id: dec-noh-program
type: decision
status: adopted
date: 2026-10-19
title: 能・狂言・歌舞伎・文楽・落語・寄席で、あらすじが無いときはスタッフ欄の演目をあらすじの枠に出す
sources:
  - tools/review/render_recommend.py
  - tools/review/user_recommender.py
  - web/theme.css
links:
  - depends_on: f-noh-program-staff
  - depends_on: dec-forms-1019
  - affects: comp-cf-worker
---
起案者の指示（2026-10-19）「能のとき、あらすじはないけど演目はわかる。演目をあらすじ代わりに同じ欄に書いてほしい」。

- render_recommend.program_text: 形式（user_recommender.form_of）が PROGRAM_FORMS（能・狂言・歌舞伎・文楽・落語・寄席）で、スタッフ欄に字があれば、その文を返す。syn_block は、あらすじが無いときにこれを「演目」の見出しを付けてあらすじの枠に出す（行の区切りはそのまま、3 行で畳んで「続きを読む」、出典「公演ページのスタッフ欄」）。あらすじがあるときはあらすじが先
- 能楽堂でかかる演劇（脚本・演出・音楽などの作り手が並ぶ）は、劇場の名前だけでは能・狂言にしない（form_of の _PLAY_ROLES）
- カードは取得のたびに Python の ticket() で作り直す（rec_card）ので、次の取得から出る。ただし題名に 能楽・狂言・歌舞伎・落語 などの語がある公演は、いまは推薦の候補から外している〔q-nonplay-in-reco〕
- 無料枠: カードの文が少し長くなるだけ。新しい取得先・保存・定期実行はない
