---
id: dec-reco-measure-first
type: decision
status: proposed
date: 2026-10-13
title: 推薦の改善は、先に測る仕組みを作ってから計算を変える
links:
  - depends_on: q-reco-eval-harness
  - supports: reco-plan-unmerged
---
提案（起案者の判断待ち）。測れない状態で信号（意味の近さ・感想の観点・重みの学習）を足しても、良くなったか分からない。持ち主 1 人のデータでは測らない（dec-no-n1-evidence）ので、まず公開版で複数の利用者の記録（提示→反応→観劇後の評価）を集める仕組みを作る。計画書の P0 と、UX 計画の「抽出の実データ検証」の両方の前提になる。
