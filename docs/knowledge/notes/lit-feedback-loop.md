---
id: lit-feedback-loop
type: finding
status: confirmed
date: 2026-10-13
title: 推薦が利用者の行動を変え、その行動で次の推薦を学ぶ「輪」で、推薦は偏りやすくなる（Chaney・Stewart・Engelhardt 2018）
sources:
  - https://www.arxiv.org/abs/1710.11214
links:
  - affects: q-favourites-seed
  - supports: lit-mnar
---
How Algorithmic Confounding in Recommendation Systems Increases Homogeneity and Decreases Utility（RecSys 2018）。シミュレーションで、推薦に影響された行動のデータで学ぶと、利用者の行動が均一になり、役に立つ度合いは上がらなかった。そのデータで評価すると、元の推薦に似た方法が有利に見える。初期の推薦の偏りが、その後の記録と推薦に残りうる根拠。要旨で確かめた。
