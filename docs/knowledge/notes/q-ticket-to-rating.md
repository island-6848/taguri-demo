---
id: q-ticket-to-rating
type: question
status: answered
date: 2026-10-18
title: 行く日が過ぎた券（購入済み）から、観劇後の評価へどう進ませるか
sources:
  - https://github.com/island-6848/taguri-demo/blob/master/docs/verification/e2e-walk-2026-10-18.md
  - https://github.com/island-6848/taguri-demo/blob/master/cloudflare/src/screens/rate.js
links:
  - affects: dec-native-cutover-now
---
通し検証〔e2e-walk-1018〕で、購入済みの公演に昨日の行く日を入れても、未評価・日記帳・今週のおすすめのどこにも評価を促す行が出なかった。Worker の記録（works）は手で足した行と取り込んだ行だけで、券（ticket）から記録を作る処理は無い（rate.js の saveWorkField の説明「purchase-derived rows are never created here」）。いまは「観劇記録を追加」で手で足し直すしかない。

issue #134 は「購入済み → 行く日時 → 観劇後の評価」を一続きの流れとしている。行く日が過ぎたら評価待ちに出すのか（記録を自動で作るのか、促すだけか）、行かなかった回をどう扱うかを起案者に決めてもらう。
