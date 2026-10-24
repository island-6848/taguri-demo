---
id: dec-same-star-grade
type: decision
status: adopted
date: 2026-10-20
title: 評価一覧のタブと分布では、星の 5 段階と 0.5 きざみの同じ星の数を 1 つにまとめる
sources:
  - cloudflare/src/screens/grade.js
  - cloudflare/src/screens/rate.js
  - cloudflare/test/grade.test.js
links:
  - affects: comp-cf-worker
---
起案者の指摘（2026-10-20）「星５がタブ２個に分かれて表示されてるんだけどなぜ？」。

分かったこと（コード）: 評価は尺度ごとの形で保存している。★（5 段階）の ★5 は "5/5"、★ 0.5 きざみ（11 段階）の ★5 は "11/11"。設定で尺度を途中で変えると、前に付けた評価は前の形のまま残る。評価一覧のタブと分布は保存した値ごとに分けていたので、表示は同じ ★5 が 2 つに割れた。

- grade.sameGrade: 5 段階の "n/5" を 0.5 きざみの "(2n+1)/11" に読み替える（★n は同じ）。評価一覧のタブ・選んだタブ（?v=）・分布と表で、この値でまとめる
- 保存してある評価は書き換えない。推薦の計算は前から尺度の中での位置（frac）で読んでいるので変わらない
