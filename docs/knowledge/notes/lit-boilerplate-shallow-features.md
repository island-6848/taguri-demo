---
id: lit-boilerplate-shallow-features
type: finding
status: unverified
date: 2026-10-18
title: ウェブページの本文と飾り（定型部分）は、語数や語の密度のような浅い特徴だけでも安く見分けられる（Kohlschütter ほか, WSDM 2010。Boilerpipe）
sources:
  - https://ir.webis.de/anthology/2010.wsdm_conference-2010.45
  - https://course.khoury.northeastern.edu/cs6200sp15/extra/07_du/Boilerplate%20Detection%20using%20Shallow%20Text%20Features.pdf
links:
  - affects: synopsis-llm-history
---
Kohlschütter・Fankhauser・Nejdl, WSDM 2010, pp.441–450。浅い特徴で文の塊ごとに本文か飾りかを分類し、複雑な手法と同等の精度を低い計算量で出した。Boilerpipe ライブラリの元。
たぐりの prep()（20 字未満の行を消す・重複行を消す・口コミとツイートの枠を構造で切る）は、この考え方の最も単純な形。行の長さの 20 字という閾値は自前の観察。要旨は検索結果の引用と抄録ページで見ただけで、本文は読んでいない。
