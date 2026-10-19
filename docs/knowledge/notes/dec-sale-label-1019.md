---
id: dec-sale-label-1019
type: decision
status: adopted
date: 2026-10-19
title: 発売の札は「発売済」「未確認」「10/25発売」（日付と発売の間を空けない）。前の文言で作ったカードは画面で読み替える。札は上の行から離す
sources:
  - tools/review/recommend2.py
  - tools/review/render_recommend.py
  - web/app.js
  - web/theme.css
  - tools/review/test_reason_works.py
  - cloudflare/test/e2e-walk.js
links:
  - supersedes: dec-sale-label-words
---
起案者の指示（2026-10-19、本番の画面の写しを添えて）「ほか会場と発売済みが近すぎるで離して。あとは、『発売済』『未確認』『◎/◎発売』に文言を揃えて」。

- 文言: 「発売日不明」→「未確認」、「10/25 発売」→「10/25発売」（時刻があれば「10/25 10:00発売」）。recommend2.onsale・render_recommend.sale_label・既定値（digest・app.py・reminder.js）。
- 本番の写しが「発売済み」のままだったのは、札がデータの取得のときに Python で作られ D1（rec_card）に置かれているため。次の取得で作り直されるまでは、web/app.js の saleLabel が画面で前の文言（発売済み・確認できず・発売日不明・「10/25 発売」）を読み替える。
- すき間: 価格帯と札を、そろって 6px 下げた（中心はそろったまま）。e2e で札の上と上の行の下の間が 9px。
- e2e: master にある PR #219・#220（観劇記録の追加の画面の作り替え）で e2e-walk の 13 段が落ちる（手を入れていない master でも同じ）。この変更は #219 の前のコミットに当てて e2e を流し、札の段が通ることを確かめた。〔q-e2e-register-rework〕
