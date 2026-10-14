---
id: user-storage-measured
type: finding
status: confirmed
date: 2026-10-14
title: 1 人が D1 に置く量は、ふつうに使って約 0.7 MB、いまの行数の歯止めの中でいちばん長い文字で埋めると約 218 MB（しかも上限の無い表があった）
sources:
  - cloudflare/migrations/0021.sql
  - cloudflare/src/free-tier.js
links:
  - supports: dec-account-cap-counted
---
すべてのマイグレーションを当てた SQLite に 1 人分を入れ、page_count × page_size の増え方で測った（手元の node:sqlite。D1 も SQLite なので近いが、D1 の数え方そのものではない）。
- ふつう（記録 300・感想 300 字・手で入れた出演 30・来場メモ 50・答えた公演 600・券 100・見逃し 20・お気に入り 50・推薦の控え 60KB）: 0.70 MB
- 最悪（記録 2,000 に感想 4,000 字、手で入れた出演 2,000 件×4 欄×4,000 字、来場メモ 2,000×4,000 字、答え 5,000 に理由 2,000 字×2、券 2,000、見逃し 500）: 218 MB
- 来場メモ（visit_note）・手で入れた出演（hand_credits）・外した記録（excluded）・まとめた記録（merges）・探してほしい題名（search_request）には件数の上限が無く、最悪はさらに大きかった。0021 で 2,000（search_request は 200）を付けた
- 1 画面を開くと読む行は、記録 300 件の人でおよそ 300〜600 行（テスト用の小さな公演一覧で、返した行と全件を読む表から見積もった。D1 の rows_read の実測ではない）
