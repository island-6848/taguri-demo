---
id: dec-hide-own-words
type: decision
status: adopted
date: 2026-10-13
title: 推薦の理由に本人の感想（「あなたの言葉」）を引かない ── デモ版もサービス版も
sources:
  - tools/review/render_recommend.py
  - tools/taguri/impressions.py
  - web/app.js
links:
  - affects: dec-recommend-compact-poster
---
起案者の指示（2026-10-13）「あなたの言葉は個人情報すぎるので表示しないで。サービス版もデモ版も」。
これまで推薦の理由の欄に、◎ を付けた作品に本人が書いた感想を「あなたの言葉 《作品》に『…』と書いています」として引いていた（`impressions.quote_row`、2026-08-24 から）。画面を人に見せたり写したりすると、個人の文がそのまま出る。
やったこと:
- サーバー側: `render_recommend.reason_rows` が `quote_row` を呼ばないようにした（Render を次に起こし直したとき・Worker で同じ画面を組むときにも出ない）
- 画面側: Render の今のサーバーは古いコードのまま動いているので、`web/app.js` が受け取った画面から `li.rs.q` を取り除く（入れ替わりで足される 1 枚にも）。デモ版（GitHub Pages）とサービス版（Workers）の両方に効く
- 感想そのものは消していない。名簿・内容の好みの材料として使うのは今までどおりで、やめたのは画面への引用だけ
`tools/taguri/test_impressions.py` の 4 件の失敗（実データが要るもの）は、この変更の前から同じく失敗している。
