---
id: eval-yahoo-aspects
type: finding
status: confirmed
date: 2026-10-14
title: 項目別の映画評価では 4 件に 1 件で項目が総合から 1 段以上ずれる。項目の重みを人ごとに学んでも総合は当たらない
sources:
  - docs/research/person-reco-eval.md
  - tools/review/eval_yahoo_aspects.py
  - https://github.com/KunalShm/Multi-Criteria-Recommendation-System
links:
  - affects: impl-rating-aspects
  - depends_on: lit-yahoo-multicriteria
  - depends_on: q-aspect-attribution-check
---
Yahoo! Movies の項目別評価（物語・演技・演出・映像・総合、13 段階、6,078 人・976 本・62,156 件）。公開の写しは利用条件が無く、映画 ID から出演者・監督に結べないので手元の集計だけ（データはリポジトリに入れない）。総合から 1 段以上ずれた項目がある評価 27%、良い項目と悪い項目が両方 2%。総合は 4 項目でほぼ説明できる（決定係数の中央値 0.945）。本人ごとに項目の重みを学んでも単純な平均より当たらない（236 人、良くなった人 48%）。詳細の割合を人ごとに学ぶ案は支持されず、固定の割合のままにする。詳細で効かせる相手を変えること自体は、出演者と結べないので確かめられていない。
