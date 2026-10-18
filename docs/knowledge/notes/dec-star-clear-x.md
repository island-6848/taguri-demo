---
id: dec-star-clear-x
type: decision
status: adopted
date: 2026-10-18
title: 星の後ろの「評価しない」をやめ、星の右端の ✕ で評価を消して未評価（null）に戻す。✕ は評価が付いているときだけ出す
sources:
  - cloudflare/src/screens/grade.js
  - cloudflare/src/screens/rate.js
  - tools/taguri/serve.py
  - web/app.js
  - web/theme.css
  - web/fonts.css
  - cloudflare/test/grade.test.js
  - cloudflare/test/fonts.test.js
  - cloudflare/test/screens/scenarios.json
  - cloudflare/test/e2e-walk.js
links:
  - depends_on: dec-star-default
  - affects: dec-font-accent-five
---
起案者の指示（2026-10-18）「『評価しない』のボタンじゃなくて、星の右端に✕ボタンをつけることでnullにできるようにして。」

前の形: 星 5 段階・0.5 きざみの後ろに「評価しない」（値は「まだ判断できない」＝HOLD、評価には数えない。2026-10-16 に星 0 の代わりに置いた）。

決めたこと:
- 星の並びの右端（★n の右）に小さな ✕（丸い薄い枠、押せる広さ 32px 四方、aria-label「評価を消す（未評価に戻す）」、title「評価を消す」）。押すと POST /api/rate {work_key, clear: true} で works.verdict を NULL に戻し、行は未評価の一覧に戻る。clear は true だけを受ける（ほかの値は今までどおり「verdict が候補にない」で断る）
- 評価が付いているときだけ出す（hidden を画面が付け外し）。理由: 付いていない行の ✕ は押しても何も起きず、「押すと何かが消えるのか」と迷わせる。未評価の一覧では全部の行に ✕ が並んでしまう。✕ は星の後ろなので、出たり消えたりしても星の位置は動かない
- 詳細（aspects）は消さない。評価が無い間は詳細の欄を隠し、付け直せば前の詳細のまま出る。消したときも評価した時刻（rated_at）は進める（評価が変わったので）
- 前に付けた「まだ判断できない」は読めるまま（星は空、✕ が出て押せば未評価に戻る）。押し口だけをやめた
- 図形（○× など）の段階は今までどおり（指示は星について）
- 書体: さわらびゴシックの指定から「評価しない」（.rb button.nograde）を外した。✕ は記号なので書体を決めない（fonts.css・fonts.test.js は 4 か所に）
- Python 版（serve.on_rate）も同じ {clear: true} を受け、同じ答えを返す（scenarios「clear a rating」）
- 電話の幅では星 5 つが 1 行に収まるよう星を 30px に詰めた（★n と ✕ は入らなければ次の行）

確かめたこと: grade.test.js（✕ の出し分け・消すと NULL・詳細が残る・まだ判断できない を消せる・clear が true 以外は断る）、Python と Worker の一致、e2e-walk の「星の右端の ✕ で評価を消し、付け直す」と写し。
