---
id: dec-reco-graded
type: decision
status: adopted
date: 2026-10-13
title: 推薦は「全部の段階を、その人基準（いつもより高いか低いか）で使う」形に変える。役職の重みの学習は入れない
links:
  - depends_on: eval-douban-graded-better
  - supersedes: dec-reco-measure-first
  - affects: comp-recommender
  - affects: q-rating-aspects
---
起案者の指示（「本当に今の推薦でいいのか検証した上で採用して」）に従い、公開データの 500 人で今の計算と比べて採用した（eval-douban-graded-better）。役職の重みの人ごとの学習は効かなかったので入れない（eval-douban-role-learning-no-gain）。観点（値段・脚本・演出など）の割り当ては、データが無く検証できていないので、入れるときは別に確かめる。演技の不満は演出家にほんの少しだけ効かせる（起案者の指示）。
