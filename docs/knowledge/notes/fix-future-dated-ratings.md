---
id: fix-future-dated-ratings
type: decision
status: adopted
date: 2026-10-18
title: 観た日（first_date）が今日より後の記録の評価は、推薦の学習（ratedWorks・裏の答え合わせ）に入れない。日付の無い記録は入れる（#116）
sources:
  - https://github.com/island-6848/taguri-demo/issues/116
  - cloudflare/src/screens/recommend.js
  - docs/impression-preferences.md
  - tools/taguri/app.py
  - cloudflare/test/recommend-screen.test.js
links:
  - affects: impl-person-ordinal-v3
---
issue #116（2026-10-18）: ratedWorks は unseen・stage_id・評価の形だけを見て、観た日が今日より後かを見ていなかった。日付の打ち間違いや先の予定に付けた評価が、観たあとの好みと同じ材料になっていた。
- 前からの決まり: docs/impression-preferences.md に「未来の記録…は学習に含めない」、オーナーの画面（tools/taguri/app.py の _apply_impression_preferences）も first_date <= 今日。サービスの推薦だけが外れていたので、同じ条件にそろえた（小さな直し）
- 直したこと: ratedWorks で (first_date || '') <= ctx.today の記録だけを使う。日付を直したり日が来たりすれば、次の計算から入る（控えの印に works の更新日時と今日がある）。評価の画面で未来の日付に評価を付けること自体は止めていない
- 画面の控えは screen-v27
- 残り（起案者の判断）: 「予定」「観劇済み」「評価済み」を画面でどう分けるか、未来の日付の記録に評価を付けさせるか。今回は学習から外すだけ
