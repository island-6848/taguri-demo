---
id: triangle-label-mismatch
type: finding
status: confirmed
date: 2026-10-13
title: 画面の△の説明「あまり合わなかった」は、起案者の考える△（まあ良いが気になる所がある）と食い違う
sources:
  - https://github.com/island-6848/taguri-demo/blob/master/tools/taguri/app.py
links:
  - raises: q-rating-scale
  - affects: comp-recommender
---
起案者（2026-10-13）:「△ってまあいいけど×にするほどではない気になるところがあるってこと」。画面の説明（app.py の VERDICT_LABEL）は △＝あまり合わなかった、× ＝合わなかった で、△を否定寄りに読ませている。今の推薦（person-feedback-v1）は◎だけを「好き」に数え、○・△・×を同じ「◎でない」として扱っている。
