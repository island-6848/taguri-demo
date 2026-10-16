---
id: impl-kind-reason-off
type: decision
status: adopted
date: 2026-10-16
title: 種類の理由（原作「オリジナル」など）に ✕ を付け、押すとその利用者のおすすめで点数にも理由にも使わない。公演は消さない
sources:
  - cloudflare/src/screens/recommend.js
  - cloudflare/src/screens/lists.js
  - web/app.js
  - cloudflare/test/kind-off.test.js
links:
  - answers: q-kind-reason-off
---
起案者「お願い」（2026-10-16、q-kind-reason-off の案）。
- 理由の種類の行（reasonRows）に `<button class="rsx" data-kindoff="#原作\tオリジナル">✕</button>`。押すと POST /api/kind_off {action: add, key}。app_setting の kind_off（JSON の配列、100 件まで、'#種類\t中身' の形だけ受ける）に控える
- rankedGroups: 評価した作品・興味あり／なし・お気に入りの種の people から、その鍵の種類（role が # で始まる行）を外してから点数を出す（withoutKinds）。値が無くなるので順位にも理由にも出ない。同じ名前の人（出演「オリジナル」など）は外さない。公演そのものは消さない（人物の ✕ ＝「出さない語」は名前が出る公演を丸ごと消すので、別の口にした）
- 控えの印（rec_cache の stamp）に外した鍵の並びをそのまま入れる。updated_at だけだと、同じ秒に外して戻したとき古い控えが残った（試験で見つけた）
- お気に入りの画面の「出さない語」の下に「使わない理由 N 件」の一覧と ✕（戻す）。1 件も無いときは出さない
- しなかったこと: Python のデモ（tools/taguri/app.py・render_recommend.py）には入れていない（本番は Worker）。「韓国原作」のような細かい種類は別の問い〔q-origin-country-tag〕
