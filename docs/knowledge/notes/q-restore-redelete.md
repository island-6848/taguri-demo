---
id: q-restore-redelete
type: question
status: open
date: 2026-10-14
title: 控えから戻したとき、控えのあとに完全削除した人の記録をどう消し直すか
links:
  - depends_on: dec-d1-backup
  - affects: dec-account-deletion
---
控え（最大 30 日前）から戻すと、その後に完全削除した人の記録が戻る。案: 削除した利用者の id（ランダムな UUID だけ。名前や記録は持たない）を 30 日だけ残し、戻したあとに消し直す。説明の文書には「削除後も最大 30 日は暗号化した控えに残る」と書く必要がある（q-privacy-law）。
