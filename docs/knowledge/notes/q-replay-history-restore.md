---
id: q-replay-history-restore
type: question
status: open
date: 2026-10-18
title: 手元の再生（replay_eval の cut_copy）は、時点 t より後に編集した行を丸ごと消すので、当時あった評価が消える。当時の値をどう戻すか（履歴の行・時点別の控え）、戻せない期間をどう結果から外すか（#113）
sources:
  - https://github.com/island-6848/taguri-demo/issues/113
  - tools/review/replay_eval.py
links:
  - affects: impl-replay-eval
---
issue #113（2026-10-18）: cut_copy は updated_at などが t より後の行を消す。10/1 に評価し 10/12 に感想だけ直した行は、t=10/5 の写しで 0 件になる。
- 一部は〔fix-rated-at〕で和らぐ: works.rated_at（評価・詳細が変わった時刻）は感想の編集では進まないので、works だけは「rated_at が t より後なら消す」にすれば感想の編集で消えなくなる（ただし評価を直した行は、直す前の値に戻らず消える）
- 測ること: 本番の控え（バックアップ）で、t ごとに「消えた評価の行数・割合」を出す。それが大きい期間は学習曲線の根拠から外す
- 決めること（起案者）: 評価の履歴を残す表（評価を変えるたびに 1 行。D1 の書き込みは評価 1 回に 1 行増え、無料枠の 1 日 10 万行の中では小さい）を足すか、日ごとの控え（taguri-backup の R2。容量と読み出しの数に注意）から時点の値を取るか
