---
id: dec-empty-guides-1024
type: decision
status: adopted
date: 2026-10-24
title: 空の画面の案内をそろえる（おすすめの見出し「たぐりへようこそ！」、公演カレンダー・評価一覧はイラスト付き、未評価 0 件は感謝）。眺めるの図の名前を「Storyline」にし、スマホで指 1 本で送れるようにした
sources:
  - cloudflare/src/screens/recommend.js
  - cloudflare/src/screens/lists.js
  - cloudflare/src/screens/calendar.js
  - cloudflare/src/screens/rate.js
  - cloudflare/src/screens/guide.js
  - tools/taguri/storyline.py
  - cloudflare/test/rate-empty.test.js
  - cloudflare/test/screens.test.js
---
起案者の指示（2026-10-24）。

**空の画面**
- おすすめ（使い始めで 0 件）: 見出し「今週のあなたへのおすすめはありません」を「たぐりへようこそ！」に。ワンポイント 1 の文を「右上の+ボタンまたは『観劇記録を追加』から、追加してください。」に。
- お気に入り（0 件）: 「上の『要素を登録』で、劇団・俳優・演出家・作品・原作者・題材などの名前を登録すると、登録した要素の公演情報が表示されます。」
- 公演カレンダー（表示できる公演が 0 件）: イラスト（暦と帯）付きの案内。「カレンダーに表示できる公演がありません。推薦の画面で『興味あり』を押した公演と、お気に入りに関連する公演の情報が表示されます。」panel（Python の stage_calendar と同じ形）は変えず、calendarScreen で出し分ける。
- 評価一覧（評価 0 件）: イラスト（券と星）付きの案内。「過去に観た舞台の評価一覧が表示されます。過去の観劇記録の追加は、右上の+ボタンまたはこちら（観劇記録を追加へのリンク）。『購入済』にした公演は、公演日時をすぎると自動的に評価一覧ページに表示されます。」未評価の記録があるときは、そこへ進む口（#94）も添える。
- 未評価（0 件で、評価は 1 件以上）: イラスト（花束）付きで「ご回答ありがとうございました！」。記録も評価も無いときは前の 1 行のまま。
- 評価一覧・未評価は Python の画面と同じ HTML かを screens.test.js で比べている。サービス版だけの案内なので、両方を同じ印に置き換えて比べ、形は rate-empty.test.js で確かめる。
- 電話の幅（390px）で目で見た。

**Storyline（眺める）**
- 「同じ作品で一緒だった人の流れ」を「Storyline」に（起案者の指示「名前を変えて」）。
- スマホで図を送れなかった原因: d3 の拡大縮小（d3.zoom）が、指 1 本の動きも受け取って送りを止めていた（touch-action も none）。指 1 本は入れ物の送りに任せ、拡大縮小は指 2 本・ホイール・マウスのドラッグだけにした（zoom の filter と touch-action: pan-x pan-y）。
- 確かめたこと: Chromium の触れる操作の再現（CDP Input.dispatchTouchEvent）で、前は指 1 本で 0px（拡大縮小として受けた）、後は 451px 送れ、指 2 本では拡大縮小が動く。説明の文に「スマホでは指 2 本で広げます。指 1 本では図を送れます」を足した。
