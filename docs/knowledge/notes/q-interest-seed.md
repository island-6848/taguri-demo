---
id: q-interest-seed
type: question
status: answered
date: 2026-10-14
title: 「興味あり」を、お気に入りと同じ仮の ◎（seeds）として推薦の材料に入れるか。重みと、一覧にしかない公演の人物をどう引くか
links:
  - depends_on: lit-feedback-loop
  - depends_on: lit-new-user-rashid
  - depends_on: lit-explicit-implicit-jawaheer
  - depends_on: interest-not-in-v3
  - affects: impl-person-ordinal-v3
---
案: 興味ありを押した公演（最大 60 件）の人物を、お気に入りより弱い z で seeds に足す。確かめること: (1) 重み（観た評価より確からしさが低い、lit-implicit-confidence）、(2) おすすめで興味ありを押す → 同じ人の公演が増える、の繰り返しで偏らないか、(3) 一覧（catalogue）にしかない公演の出演欄を人物に直す手間と、Workers Free の 10 ms の CPU に収まるか。起案者の判断を待つ。

2026-10-14 追記: 起案者の指摘「お気に入りってそもそも推薦に入ってこないのでは。興味ありをお気に入りより軽くする意味がわからない」。文献（lit-implicit-confidence・lit-pre-post-consumption）が裏付けるのは「観る前の信号は、観た後の評価より確からしさが低い」までで、お気に入りより軽くする根拠は無い。しかも、お気に入りの仮の ◎ は「その人が出ている公演」を推して作るが、興味ありは本人がその公演を選んでいるので、1 公演あたりの手がかりはむしろ確か。案を「お気に入りと同じ重み（z = 0.4√12、重み 3/(3+評価の数)、評価が増えるほど薄まる）」に改めた。偏りの注意は lit-feedback-loop、早い段階の材料にする意義は lit-new-user-rashid。
