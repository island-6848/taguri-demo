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
2026-10-13 追記（推薦側のセッションから）: v2 のブランチを段 1 の master（c473394）の上に載せ直し、衝突なく JS 54 件・cloudflare の Python・test_user_recommendation が通った。v2 には評価の段階を利用者が選べる対応（「値/段階数」、◎○△× は 4 段階）も入っている。master に入れるかは起案者の判断待ち。段 2（おすすめ）の移行はこれを正解にして進めるので、入るまで待つ。
