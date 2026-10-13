---
id: dec-reco-measure-first
type: decision
status: superseded
date: 2026-10-13
title: 推薦の改善は、先に測る仕組みを作ってから計算を変える
links:
  - depends_on: q-reco-eval-harness
  - supports: reco-plan-unmerged
---
提案（起案者の判断待ち）。測れない状態で信号（意味の近さ・感想の観点・重みの学習）を足しても、良くなったか分からない。測り方は利用者ごと（dec-reco-per-user-eval）。利用者をまたいで記録を集めることはしない。計画書の P0 と、UX 計画の「抽出の実データ検証」の両方の前提になる。
