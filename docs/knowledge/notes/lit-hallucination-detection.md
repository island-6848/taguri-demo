---
id: lit-hallucination-detection
type: finding
status: unverified
date: 2026-10-18
title: LLM の作り話を見つける方法には、何度も生成させて食い違いを見る方法（SelfCheckGPT）と、原子的な事実に分けて出典で裏付けを数える方法（FActScore）がある
sources:
  - https://arxiv.org/abs/2303.08896
  - https://aclanthology.org/2023.emnlp-main.557
  - https://aclanthology.org/2023.emnlp-main.741
links:
  - affects: synopsis-llm-history
---
SelfCheckGPT（Manakul・Liusie・Gales, EMNLP 2023）: 外部の資料も確率も使わず、同じ問いで複数回生成させ、文ごとの一致の度合いで作り話を見つける。
FActScore（Min ほか, EMNLP 2023）: 生成文を原子的な事実に分け、信頼できる資料で裏付けられる割合を数える。人手では ChatGPT の伝記が約 58%。自動版は誤差 2% 未満とされる。
たぐりの verbatim()（12 字の窓 5 つ中 3 つ）は、出典（取ったページ本文）が手元にあるので、FActScore に近い「出典と照らす」型を最も単純にしたもの。ただしあらすじだけを照らしていて、題材の言葉は照らしていない（〔q-synopsis-lit-gaps〕）。要旨は検索結果の引用と抄録ページで見ただけで、本文は読んでいない。
