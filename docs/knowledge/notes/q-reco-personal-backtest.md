---
id: q-reco-personal-backtest
type: question
status: open
date: 2026-10-13
title: その人の記録だけで、計算方式の良し悪しをどう確かめるか（振り返りでの検証）
links:
  - depends_on: dec-reco-per-user-eval
  - affects: comp-recommender
---
案: 公演に結び付いた記録を観た日の順に並べ、ある日より前の評価だけで後の公演に点を付け、あとで◎だった公演ほど点が高いか（◎と×・△の順序がどれだけ合うか）を数える。新しい記録は要らず、その人の D1 の行と索引（rec_people）だけで計算できる。記録が少ないうちは数がぶれるので、件数と一緒に出し、断定しない。
