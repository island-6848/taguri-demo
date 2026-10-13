---
id: gemini-budget-cap
type: finding
status: confirmed
date: 2026-10-13
title: LLM の呼び出しには月の上限がある（既定 300 回）
sources:
  - tools/llm_gemini.py
links:
  - affects: comp-catalog-pipeline
verifies:
  - S27
---
`GEMINI_MAX_CALLS_PER_MONTH` を超えると呼ぶ前に止まる。数えた記録はホームディレクトリの下に置く。
