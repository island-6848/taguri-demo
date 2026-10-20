---
id: dec-watched-unrated-seed
type: decision
status: adopted
date: 2026-10-20
title: 観劇記録にある公演はおすすめから外し、まだ評価していない記録は購入済みと同じ推薦の種にする（評価したら評価 1 回分に替わる）
sources:
  - cloudflare/src/screens/recommend.js
  - cloudflare/test/watched-reco.test.js
links:
  - affects: comp-cf-worker
---
起案者の指摘（2026-10-20）「観劇記録に追加しても、すぐにおすすめ欄に反映されてる感じしない」。

調べたこと（コードと手元の試験）:
- 控えは原因ではない。書き込むたびに users.rec_rev が進んで rec_cache の印が変わり、画面の控え（fragmentCache）も post のたびに捨てる。service worker は /api/ を控えない
- 原因 1: 推薦の材料は「公演に結び付き、評価があり、観た日が今日以前」の記録だけ（ratedWorks）。足した直後の記録は未評価なので何も効かなかった
- 原因 2: おすすめから外すのは答えた公演（reaction）だけで、観劇記録にある公演は外していなかった。手元の試験で、おすすめに出ていた公演を記録に足しても、◎ を付けても出たままだった

決めたこと:
- 観劇記録にある公演（stage_id のある記録）は、答えた公演と同じくおすすめから外す（同じ公演の別の会場も sameProduction で外れる）
- まだ評価していない記録の公演は、購入済み（interestSeeds の owned）と同じ種にする。評価したら種から外れ、評価 1 回分に替わる（2026-10-19 の購入済みと同じ規則）。観た日が先の記録（評価を学ばない）も種のまま
- 画面の版 screen-v40
