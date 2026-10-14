---
id: pr14-reason-kinds
type: finding
status: unverified
date: 2026-10-14
title: PR #14 で、おすすめは「点を上げた人物」か「公演の種類（#形式・#原作・#翻訳・#題材）」がある公演だけになり、/api/recommend の reasons に種類が入る
sources:
  - https://github.com/island-6848/taguri-demo/pull/14
links:
  - affects: dec-reason-work-titles
  - affects: q-pr14-free-tier
---
別のセッション（session_011h35PdoJgoX8yQQagUsiJf、2026-10-14 04:57 UTC の知らせ。情報として扱い、PR の差分ではまだ確かめていないので unverified）。
- 起案者から「理由を出せていません」が多すぎると指摘があった。原因はクレジットの無い公演が「劇場が同じ」だけで上位に入っていたこと
- 対策: 点を上げた人物か、公演の種類（#形式・#原作・#翻訳・#題材）がある公演だけをおすすめにする
- Worker の /api/recommend の items[].reasons は人物で 3 つまで、空きを種類で埋める。種類の reason は role が「#形式」「#原作」「#翻訳」「#題材」「#会場」「#値段」、person がその値（例 {role:'#形式', person:'ミュージカル', n:3}）。「#」で始まる role は人物ではなく種類として書く（「形式 ミュージカル」）
- 推薦の版の印は 'person-ordinal-v3+fav3+asp1+tour1+why1'
- デモ版（Python）の理由の行は、あちらが render_recommend の「種類」の行として直した

こちらの側への影響（master の fde2770 で確かめた）:
- web/app.js は items[].reasons を読まない（おすすめの画面は Python が作り、Worker が橋渡しする）。「なぜ気になったか」の名前のタグ（noteNames）も画面の出演・作り手・団体の欄から拾うので、種類の reason は混ざらない
- 理由に作品名を書く（dec-reason-work-titles）の works_text と、あちらの「種類」の行が render_recommend.py で重なる。PR #14 が master に入ったら、取り込んだ後に理由の行の試験（test_reason_works.py）が通るかを確かめる
