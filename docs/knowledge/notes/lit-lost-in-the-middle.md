---
id: lit-lost-in-the-middle
type: finding
status: unverified
date: 2026-10-18
title: LLM は長い入力の真ん中にある情報を使いにくく、最初か最後にあるときがいちばん正確（Liu ほか 2023、TACL 2024）
sources:
  - https://arxiv.org/abs/2307.03172
  - https://preview.aclanthology.org/setup/2024.tacl-1.9
links:
  - affects: synopsis-llm-history
---
複数文書の質問応答と鍵-値の引き当てで、正解の位置を動かして測った。U 字型で、長い文脈向けのモデルでも真ん中で落ちる。入力が長いほど全体も下がる。
たぐりは本文を CoRich 2,500 字・公式 3,500 字に切り、20 字未満の行を消してから渡す（extract_theme_llm.py の prep）。あらすじがページの中ほどにあると読み落としやすい可能性があるが、たぐりの入力の長さ（千数百字）で効くかは測っていない。要旨は検索結果の引用と抄録ページで見ただけで、本文は読んでいない。
