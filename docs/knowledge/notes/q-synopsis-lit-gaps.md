---
id: q-synopsis-lit-gaps
type: question
status: open
date: 2026-10-18
title: あらすじの読み取りを文献と比べて見えた穴（題材の言葉が本文と照らされていない・別の公演の本文の引き写しは検査で止まらない・窓と閾値の根拠）を、どの順で測って直すか
sources:
  - tools/credits/extract_theme_llm.py
links:
  - depends_on: lit-hallucination-detection
  - depends_on: lit-grounding-string-match
  - depends_on: lit-llm-keyphrase-zeroshot
  - depends_on: lit-lost-in-the-middle
  - depends_on: q-prompt-g2-base
  - affects: synopsis-llm-history
---
起案者「それ論文に基づいてる？」「調べてみて」（2026-10-18）。抽出の部分は論文に基づいておらず、自前の失敗例と手で付けた見本で作ってきた。文献と比べると:

1. **題材の言葉が本文と照らされていない。** あらすじは verbatim() で照らすが、言葉は照らさない。FActScore 型（言葉ごとに本文に根拠があるか）を、LLM を使わずにやるなら「言葉かその言い換えが本文にあるか」の辞書照合になる。言い換え（例: 惹かれて→恋愛）を許す方針と両立させる方法が要る。〔lit-hallucination-detection〕
2. **別の公演の本文の引き写しは verbatim() を通る。** 本文に実在するから。g1 の自問（〔q-prompt-g2-base〕）が狙ったのはこれ。文献の文字列照合〔lit-grounding-string-match〕は「どの公演の話か」までは確かめない。
3. **12 字・5 窓・3 つ以上の閾値に根拠が無い。** 手で付けた見本で、窓の長さと数を振って落ちすぎ・通しすぎを測れる（手元で回すので無料枠に影響しない）。
4. **言葉の抽出の精度は「一般名詞への言い換え」で測る物差しが学術の鍵語抽出と違う。** 比べるなら同じ見本で人手の正解と比べるしかない。〔lit-llm-keyphrase-zeroshot〕
5. 入力の真ん中を読み落とす傾向〔lit-lost-in-the-middle〕は、千数百字では小さいと見込むが未確認。

paper-trail（論文の記録）はこのセッションでつながっていないので、そちらには記録していない。
