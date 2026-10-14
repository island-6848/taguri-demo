---
id: reco-base-rate-relative
type: finding
status: confirmed
date: 2026-10-13
title: 今の計算は「その人の◎の割合」を差し引くので、◎が珍しい人の◎ほど強く効き、◎ばかりの人の◎はほとんど効かない
sources:
  - https://github.com/island-6848/taguri-demo/blob/master/tools/review/user_recommender.py
links:
  - affects: q-rating-scale
  - affects: comp-recommender
---
寄与＝（その人物の作品で◎だった割合を (◎+1)/(観た数+2) で均したもの）−（本人の全体の◎の割合）。例: 2 本観て 1 本◎の人物は、全体の◎が 1 割の人なら 0.5−0.1＝+0.4、8 割の人なら 0.5−0.8＝−0.3 で点にならない。2 本とも◎でも 0.75−0.8＜0 で、◎ばかり付ける人には推薦がほとんど出ない。辛口の人の◎を重く扱う仕組みはすでに入っているが、甘口の人の扱いが厳しすぎる。
