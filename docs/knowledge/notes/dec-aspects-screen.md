---
id: dec-aspects-screen
type: decision
status: adopted
date: 2026-10-14
title: 評価の「詳細」の画面 ── 評価を付けた記録に 8 項目×良かった／ふつう／気になった。出し方は あっさり（既定）／詳しく
sources:
  - web/app.js
  - web/theme.css
  - tools/taguri/serve.py
  - tools/taguri/app.py
  - cloudflare/src/screens/rate.js
  - cloudflare/src/screens/row.js
  - cloudflare/test/screens/scenarios.json
links:
  - answers: q-pr13-aspects-screen
---
起案者の指示（2026-10-14）「詳細の画面を作って」。仕様は推薦側（PR #13）から来たもの。
- 評価一覧・未評価の行（rec-row）で、◎○△× が付いた記録に「詳細」を出す。8 項目（話・脚本・構成／演出・見せ方／演技・出演／歌・音楽／ダンス／美術・衣裳／値段／会場・座席）それぞれに 良かった／ふつう／気になった。閉じていても、見出しの横に「良かった: … ／気になった: …」の要約を出す
- 押すたびに保存: POST /api/rate {work_key, aspects}（verdict を送らないときは詳細だけを書く）。形は rate_performances.clean_aspects（気になった＝コード、良かった＝+コード、ふつうは書かない、知らない項目・両方は断る）。Render（serve.on_rate・app.save_work_field）と Worker（screens/rate.js の rateAction）で同じ答え・同じ断り文句（試験の scenario「rating aspects」）。評価を押し直しても詳細は残る
- 行には data-aspects（今の詳細）を載せ、画面（app.js の aspectsPanel）が組み立てる
- 出し方の設定: 設定の画面に「評価の詳細の出し方」── あっさり（既定。閉じておく）／詳しく（開いて出す）。表示だけの設定なので、その端末に覚える（localStorage）。アカウントに持たせるかは、使ってみてから
2026-10-14 追記: 起案者の指示「よかったはボタンじゃなくてスライダーで」で、項目ごとの 3 つのボタンをつまみ（左＝気になった・まん中＝ふつう・右＝良かった）に替えた。離したときに保存する。

2026-10-18 追記: 起案者の指示で 5 段階（とても気になった〜とても良かった）と、項目ごとの ✕「この作品には無い」を足した〔dec-aspects-five-levels〕。前の 3 段階の記録は同じ言葉の段階として読む。
