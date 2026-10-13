---
id: rating-mixes-aspects
type: finding
status: confirmed
date: 2026-10-13
title: 観劇の評価は内容だけでなく、値段に見合うか・構成・演出などが混ざって 1 つの記号になる
sources:
  - https://github.com/island-6848/taguri-demo/blob/master/tools/review/user_recommender.py
links:
  - raises: q-rating-aspects
  - affects: comp-recommender
---
起案者の指摘（2026-10-13）:「この値段に見合ってない内容だったり構成だったり演出だったりのときに評価下げることもある」。今の推薦は評価を 1 つの値として、関わった人物全員に同じように効かせるので、値段が理由で△にした公演でも出演者まで下がる。カタログには料金（price）の欄がある（build_recommend_index.py の PUBLIC_KEYS）。
