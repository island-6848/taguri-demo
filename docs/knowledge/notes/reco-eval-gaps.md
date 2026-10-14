---
id: reco-eval-gaps
type: finding
status: confirmed
date: 2026-10-13
title: 推薦の良し悪しを測る仕組みが足りない（利用者ごとの時系列評価・正解データ・提示と結果の結び付け）
sources:
  - https://github.com/island-6848/taguri-demo/blob/master/docs/recommendation-ux-design.md
  - https://github.com/island-6848/taguri-demo/blob/master/docs/recommendation-exposure-verification.md
links:
  - raises: q-reco-eval-harness
---
既存の測定スクリプト（tools/review/measure_*.py など）は持ち主の私有データが前提。利用者ごとの時系列のオフライン評価（計画書の evaluate_user_learning.py）は提案だけ。提示ログはあるが、反応・観劇後の評価と結び付けていない（candidate_reacted・outcome_rated は未実装）。見本の 96 件は架空なので評価に使えない。
