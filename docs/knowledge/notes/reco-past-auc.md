---
id: reco-past-auc
type: finding
status: unverified
date: 2026-10-13
title: 過去の改善の実験結果（持ち主 1 人の評価での AUC）は、判断の根拠に使わない
sources:
  - https://github.com/island-6848/taguri-demo/blob/master/tools/review/recommend2.py
links:
  - affects: comp-recommender
---
◎だけを正例 0.744／○以上 0.556、役職単独で出演 0.611・演出脚本 0.540・裏方 0.500、上位 3 件の和 0.643（単独 0.615）、申告を加点に混ぜると 0.744→0.660、並び順の段を外すと 0.692→0.710、あらすじの要素（網 C）単独 0.551±0.167 で B に足して上がった回は 0/40。注記が指す docs/verification/0xx はどのブランチにも無い。1 人のデータなので公開版の精度には使えない（計画書 §7.1）。

起案者の指示（2026-10-13）:「実験結果は信用しないで。n=1 なので」。数値がコードに残っていることは事実だが、1 人分のデータなので、どの改善が効くかの根拠にはしない。
