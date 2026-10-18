---
id: q-replay-h3-satisfaction
type: question
status: open
date: 2026-10-18
title: 評価の計画の H3（観る前の点と観たあとの評価の順位相関）を、手元の再生（replay_eval）にまだ実装していない。興味の指標（H1）と満足の指標を分けて出す（#114、測る道具を作る）
sources:
  - https://github.com/island-6848/taguri-demo/issues/114
  - tools/review/replay_eval.py
  - docs/research/real-data-eval-plan.md
links:
  - depends_on: plan-real-data-eval
  - affects: impl-replay-eval
---
- 作るもの: 答えたときの点（reaction.score・ver）または表示の記録（rec_shown）と、のちの本人の評価（works.verdict、時刻は〔fix-rated-at〕の rated_at）を公演で結び、Kendall τ を人ごとに出す。観なかった公演は満足の負例にしない。評価まで行った公演の偏り（買った人だけが評価する）と欠測の数も出す
- 推薦の計算は変えない（測るだけ）。D1 には何も足さない（控えのバックアップを手元で読む）
