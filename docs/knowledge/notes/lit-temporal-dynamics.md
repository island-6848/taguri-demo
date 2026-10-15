---
id: lit-temporal-dynamics
type: finding
status: unverified
date: 2026-10-15
title: 好みは時間とともに変わるので、古い評価と新しい評価を同じに扱わず、時間の変化をモデルに入れると精度が上がった（Koren, KDD 2009 最優秀論文）
sources:
  - https://faculty.cc.gatech.edu/~zha/CSE8801/CF/kdd-fp074-koren.pdf
links:
  - affects: impl-person-ordinal-v3
---
Collaborative Filtering with Temporal Dynamics。古いデータを捨てる・一律に薄めるのではなく、利用者ごとの変化を追う形を提案し、Netflix のデータで精度が上がった。たぐりの personValues は、観た日にかかわらず評価を同じ重さで数える（コードで確認）。10 年前の ◎ と先月の ◎ が同じに効く。要旨は検索結果の引用で見ただけ。
