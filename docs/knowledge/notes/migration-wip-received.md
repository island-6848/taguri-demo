---
id: migration-wip-received
type: finding
status: confirmed
date: 2026-10-13
title: 段 1 の作りかけを受け取った。読み込めない原因は py.js の正規表現に入った生の行区切り文字だった
sources:
  - https://github.com/island-6848/taguri-demo/commit/7da8985
  - https://github.com/island-6848/taguri-demo/commit/165358c
links:
  - answers: q-migration-branch
  - affects: migration-handover-stage0
---
別セッション（session_011h35PdoJgoX8yQQagUsiJf）が 2026-10-13 に wip-screens-port（7da8985）を push した。中身: src/screens/rate.js（評価・未評価・感想の 3 画面と add_work・rate・note）、row.js（_rec_row・_edit_html の移植途中）、works.js、py.js の追加分、migrations/0011.sql と scripts/build_stage_labels.py、test/screens/catalogue.py の拡張。止めた位置は感想の画面の _pending_notes_html。
JS の試験がすべて落ちていた原因は、py.js の dumps の正規表現リテラルに U+2028/U+2029 が生で入っていたこと（JS では行の終わりとして扱われる）。置き換え自体が何もしない処理だったので外し、master と合わせたうえで JS の試験 48 件・Python の試験が通った。
ただし scenarios.json はまだ空で、Python と同じ HTML が出るかは 1 画面も確かめていない。
