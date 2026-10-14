---
id: eval-douban-scales
type: finding
status: confirmed
date: 2026-10-13
title: 評価の段階を粗くしても当たりは少し下がるだけで、途中で段階を変えた人は「同じ段階どうしで比べる」のがよい
sources:
  - docs/research/person-reco-eval.md
  - tools/review/eval_rating_scales.py
links:
  - supports: dec-user-scale-range
  - affects: comp-recommender
---
公開の映画評価（500 人、5 段階を丸めて 2〜4 段階を作った）。4 段階は 5 段階とほぼ同じ、2・3 段階は AUC が 0.015 ほど下がる。前半 5 段階・後半 2〜3 段階に変えた場合、同じ段階の評価どうしで「いつもより高いか低いか」を出す扱いが、0〜1 に引き伸ばしてまとめる扱いと同じか良く（5→2 で +0.004〜0.008）、変えたあとの評価だけを使う扱いより +0.03 良い。6〜11 段階はこのデータでは確かめられない。この扱いを person-graded-v2 に入れた（評価は「値/段階数」、例 4/5 で保存。◎○△× は 4 段階）。
