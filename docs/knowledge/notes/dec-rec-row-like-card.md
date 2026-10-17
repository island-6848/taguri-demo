---
id: dec-rec-row-like-card
type: decision
status: adopted
date: 2026-10-18
title: 評価一覧・未評価・日記帳の 1 件を、おすすめのカードと同じ形にした（団体・会場の行、作り手、囲んだあらすじ、ポスターなしの地）
sources:
  - cloudflare/src/screens/rowinfo.js
  - cloudflare/src/screens/row.js
  - cloudflare/src/screens/rate.js
  - cloudflare/src/screens/diary.js
  - web/app.js
  - web/theme.css
  - cloudflare/test/rowinfo.test.js
  - cloudflare/test/screens.test.js
links:
  - depends_on: dec-recommend-ui-1017
---
起案者の指示（2026-10-18）「評価一覧や日記帳のカードもおすすめと揃えて」。
- 確かめたこと: 評価一覧・未評価の行は、つながった公演の作り手もあらすじも読んでいなかった（題名・日付・評価だけ）。日記帳は出演・演出・脚本だけ（作・原作は無く、あらすじは空）。ポスターの無い行は灰の箱だけで、おすすめの「題名＋ポスターなし」と違っていた
- 直したこと: 1 枚に出す分（15 件。未評価は全件）の公演について、団体・会場・作り手・あらすじを読む（rowinfo.js。stageInfo＝公演・一覧・手で直した欄、カードのあらすじ、過去の公演の会場。どれも stage_id の主キーで引く）。画面（compactRows）がおすすめと同じ部品で組む: 団体と会場は絵記号付きの行、作・原作・脚本・演出は必ず、ほかは設定で選んだ役職だけ（おすすめと同じ設定）、あらすじは囲んで 100 字ほど・続きは畳む
- 読み取りの増え方: 1 回の表示で数本の問い合わせ・数十行。D1 の読み取りの無料枠（1 日 500 万行）に対して小さい
- 評価の押し口（星・判子）は、前の指示（2026-10-16「星の位置を会場の下に」）どおり会場のすぐ下のまま。おすすめの回答ボタンとは役目が違うので形は揃えていない
- Python との一致の試験: この欄はサービス版だけの形なので、記録を直す欄と同じく比べから外し、rowinfo.test.js で形を確かめる
- 分からないこと: 出演の並びは名前の順（rec_people を役職・名前で並べ直しているため）。おすすめのカードは公演ページの出演順
