---
id: q-reco-learning-design
type: question
status: open
date: 2026-10-13
title: 「使うほど精度が上がる」推薦をどう作るか（何を好きとし、何を精度の向上とするか）
links:
  - depends_on: dec-reco-per-user-eval
  - affects: comp-recommender
---
案（2026-10-13）: 正解は観劇後の本人の評価、観る前の反応は確からしさの低い信号。人ごとに手がかりの重みを、既定の重みを事前として組で比べる学習で寄せる。精度は届いた順の予想と答え合わせで裏で測り、既定より確かに良いときだけ使う。文献で裏付けた点と、直すべき点（反応しなかった公演の扱い・事前分布を全員から学べないこと・多様さ）は lit-* の各項目。
