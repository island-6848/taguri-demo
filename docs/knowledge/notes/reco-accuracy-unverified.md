---
id: reco-accuracy-unverified
type: finding
status: confirmed
date: 2026-10-13
title: 今の推薦（person-feedback-v1）の精度は、公開版の利用者では測っていない
sources:
  - https://github.com/island-6848/taguri-demo/blob/master/docs/user-recommendation-loop.md
  - https://github.com/island-6848/taguri-demo/blob/master/tools/review/user_recommender.py
links:
  - affects: comp-recommender
  - raises: q-reco-eval-harness
---
人物ごとの寄与＝（◎の割合−本人の全体◎率）×確からしさ×役職の重み、上位 3 件の和。係数は公開利用者向けに検証していない。すべて◎の履歴・履歴なしでは点が付かないことがある。人物情報の無い記録は効かない。テストは動作の確認で、精度の確認ではない。
