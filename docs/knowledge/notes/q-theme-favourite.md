---
id: q-theme-favourite
type: question
status: answered
date: 2026-10-14
title: 題材のお気に入りを推薦の種に使うには、あらすじの題材を Worker の索引に入れる必要がある
links:
  - depends_on: eval-favourite-kinds
  - affects: comp-recommender
---
Render の画面は、題材のお気に入りをあらすじから取り出した要素（net_c の語）と照合している（recommend2.declared_hits）。Worker の索引（rec_*）にはあらすじも要素も無いので、題材のお気に入りから種の公演を引けない。ジャンルで代えた確認では評価 0〜3 件で効いた（eval-favourite-kinds）。入れるなら、索引を作るときに公演ごとの題材の語を「#題材」のタグとして rec_credit / rec_people に足すのが今の作りに合う（公演の種類と同じ扱い）。行数（D1 の書き込み枠）と、題材の語の質を確かめてから。
