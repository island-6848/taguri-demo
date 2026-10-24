---
id: dec-form-rodokugeki
type: decision
status: adopted
date: 2026-10-19
title: 形式の札「朗読」を「朗読劇」に改める。外していた人の設定（kind_off）は migration 0043 で新しい名前に移す
sources:
  - tools/review/user_recommender.py
  - cloudflare/migrations/0043.sql
  - cloudflare/test/migrations-keep-records.test.js
links:
  - depends_on: f-form-rodoku-1019
  - affects: dec-forms-1019
---
起案者の指示（2026-10-19）「『朗読劇』に名前変えて」。

- user_recommender._FORM_TITLE の札を "朗読劇" に。当たる語（題名の 朗読・リーディング）と順は変えない
- 「この種類を理由に出さない」で "#形式\t朗読" を外していた人は、0043 で "#形式\t朗読劇" に書き換える（app_setting の kind_off の行だけ。0035 のトリガーで rec_rev が進み、おすすめの控えも作り直される）
- 索引（rec_people・rec_credit・past_stage.people）の札は、次の取得で推薦の索引を作り直したときに差分で入れ替わる。それまでは前の「朗読」の札のまま出る
- 無料枠: 書き込みは kind_off に「朗読」がある人の 1 行（＋users 1 行）と、索引の朗読の公演の行の入れ替えだけ
