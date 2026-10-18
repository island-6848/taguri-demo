---
id: q-prompt-g2-base
type: question
status: open
date: 2026-10-18
title: あらすじの読み取りの今の版 g2 は c6 から作られていて、g1 で足した「題名の公演自身の物語か」の自問が入っていない。意図どおりか、g1 の上に g2 を重ねるべきか
sources:
  - tools/credits/extract_theme_llm.py
links:
  - affects: synopsis-llm-history
  - affects: dec-synopsis-reader-claude
---
`tools/credits/extract_theme_llm.py` の `PROMPT_G2 = _sub(PROMPT_C6, …)`。g1 は `PROMPT_G1 = _sub(PROMPT_C6, …)` で、
別の公演のあらすじ（劇団紹介に載った代表作など）を拾わないための自問と例を足した版。g2 は同じ c6 から
「人物の関係を具体的な語に」「倫理・社会の論点も語に」を足したので、**g1 の自問は g2 に入っていない**（2026-10-18、コードで確かめた）。

分からないこと: 測り直しのために、わざと c6 を土台にしたのか（コメントには c2〜c6 の文面は変えない、とだけある）。
g1 の効果は検証 050 の道具で測られたはずだが、その結果はこのリポジトリに無い（data/ は入っていない）。
別の公演の物語の混入（例: 流浪樹に妊活・闇バイト）は g1 が狙った失敗なので、g1＋g2 を同じ標本で測ってから決める。
