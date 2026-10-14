---
id: q-interest-seed
type: question
status: open
date: 2026-10-14
title: 「興味あり」を、お気に入りと同じ仮の ◎（seeds）として推薦の材料に入れるか。重みと、一覧にしかない公演の人物をどう引くか
links:
  - depends_on: interest-not-in-v3
  - affects: impl-person-ordinal-v3
---
案: 興味ありを押した公演（最大 60 件）の人物を、お気に入りより弱い z で seeds に足す。確かめること: (1) 重み（観た評価より確からしさが低い、lit-implicit-confidence）、(2) おすすめで興味ありを押す → 同じ人の公演が増える、の繰り返しで偏らないか、(3) 一覧（catalogue）にしかない公演の出演欄を人物に直す手間と、Workers Free の 10 ms の CPU に収まるか。起案者の判断を待つ。
