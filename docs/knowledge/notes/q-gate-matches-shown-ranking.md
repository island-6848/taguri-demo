---
id: q-gate-matches-shown-ranking
type: question
status: open
date: 2026-10-18
title: 裏の答え合わせ（chooseVariant）は、評価だけの personValues と自前の stageScore で方式を比べ、本人の効かせ方の倍率・お気に入り・興味あり・1 段広げる・表示の選別を入れない。表示の計算と同じ条件で比べると、選ぶ方式は変わるか（#115）
sources:
  - https://github.com/island-6848/taguri-demo/issues/115
  - cloudflare/src/reco-gate.js
  - cloudflare/src/screens/recommend.js
links:
  - affects: impl-hidden-gate
---
- 測ること: 出演者や内容を「効かせない」にした利用者、興味あり中心の利用者で、gate の勝敗と、実際の候補順位（同じ倍率を掛けた scoreFromIndex）の勝敗が食い違う割合。人工の利用者（reco-gate.test.js の user・priceUser・castStoryUser）に本人の倍率を掛けた版を足せば手元で測れる
- CPU の心配: 答え合わせは区切りごとに personValues を計算し直す（評価 120 件で最大 20 回）。お気に入り・興味ありまで入れると、その分の読み出しと計算が増える（〔q-reco-screen-cpu-20-ratings〕）
- 決め方の案: (1) 本人の倍率だけを答え合わせにも掛ける（読み出しは増えない） (2) 倍率を変えた利用者・興味ありの多い利用者では base のままにする (3) いまのまま。手元の測りで (1) が base より悪くならないなら (1)
