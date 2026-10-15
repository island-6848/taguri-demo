---
id: peer-star5-branch
type: finding
status: unverified
date: 2026-10-14
title: 別のセッションが、評価の初期設定を星 5 段階（保存は "n/5"）にする変更をブランチ claude/demo-records-setup-yqo65u に置いた（PR 前・起案者の返事待ち）
sources:
  - https://github.com/island-6848/taguri-demo/tree/claude/demo-records-setup-yqo65u
links:
  - affects: impl-person-ordinal-v3
---
相手のセッションの知らせ（2026-10-14）による。星のボタンは ◎○△× と同じ .rb の中に class="star" で並ぶので、未評価の評価ボタンの左寄せ（.rec-row .rb）は星にもそのまま効く。row.js で変わるのは gradeButtons(scale) と gradeText だけ。推薦（recommend.js gradeOf）はもとから "n/5" を読める。ブランチのファイルはまだ自分では読んでいない。

2026-10-15 追記（相手のセッションの知らせ、a835df1）: 評価の付け方を設定で選べるようにする（○×＝n/2、○△×＝n/3、◎○△×、星 5 段階＝n/5、0.5 きざみ＝n/11）。recommend.js の理由の並びは markRank(v) ＝ 3×(1−段階の中の位置) にし、興味あり（4）は残す。推薦の gradeOf は MIN_LEVELS 2〜MAX_LEVELS 11 を読めるので、どの段階も計算に入る。PR 前・起案者の返事待ち。ブランチのファイルはまだ自分では読んでいない。
