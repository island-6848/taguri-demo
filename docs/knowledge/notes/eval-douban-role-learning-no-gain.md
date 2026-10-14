---
id: eval-douban-role-learning-no-gain
type: finding
status: confirmed
date: 2026-10-13
title: 役職（出演・監督）の重みを人ごとに学んでも、この条件では良くならなかった
sources:
  - docs/research/person-reco-eval.md
links:
  - affects: q-reco-learning-design
---
docs/research/person-reco-eval.md。その人の記録の中で試して既定より 0.02 以上良いときだけ切り替える形で、ほとんど切り替わらず、平均もほぼ同じ。
