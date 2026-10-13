---
id: reco-v2-index-compatible
type: finding
status: confirmed
date: 2026-10-13
title: 推薦の計算 person-graded-v2 は、D1 の索引の作り（表と行）を変えない
sources:
  - https://github.com/island-6848/taguri-demo/blob/claude/demo-records-setup-yqo65u/cloudflare/scripts/build_recommend_index.py
links:
  - affects: dec-d1-catalogue-delivery
---
推薦側のセッション（session_011h35PdoJgoX8yQQagUsiJf）から共有（2026-10-13）: 起案者の指示で推薦の計算を person-graded-v2 に変えた（ブランチ claude/demo-records-setup-yqo65u、master には未マージ）。
master との差分を見ると、cloudflare/scripts/build_recommend_index.py で変わるのは要求ごとの計算（score_from_index）だけで、build_index・to_sql・表（rec_stage・rec_credit・rec_people・rec_gram）は変わらない。したがって deliver_catalogue.py が入れる索引は v2 のマージ後もそのまま使える。Worker 側の計算（recommend.js）と rec_cache の鍵は v2 で変わる。
画面の移植で Python の推薦画面を正解にしている場合、マージ後は v2 の出力が正解になる。
