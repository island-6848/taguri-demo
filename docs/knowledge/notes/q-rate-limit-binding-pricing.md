---
id: q-rate-limit-binding-pricing
type: question
status: open
date: 2026-10-18
title: Workers の Rate Limiting の結び付けは無料プランで料金・回数の上限があるか
links:
  - depends_on: cf-free-tier-snippets-1018
  - affects: dec-rate-limit
---
src/rate-limit.js は「Workers Free で無料」と書いているが、2026-10-18 の検索では料金表に結び付けの記載が見つからなかった（公式ページは直接開けない）。要求ごとに 1〜2 回呼ぶ。公式の Rate Limiting の文書と Workers の料金表を直接開いて確かめる。
