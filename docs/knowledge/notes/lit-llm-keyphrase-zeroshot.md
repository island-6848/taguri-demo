---
id: lit-llm-keyphrase-zeroshot
type: finding
status: unverified
date: 2026-10-18
title: LLM に指示だけで文章から鍵語を抜かせる方法は、初期の測定では従来の手法に及ばず、後の研究では新しいモデルで追いついた（Song ほか 2023、Kang・Shin 2025）
sources:
  - https://arxiv.org/abs/2312.15156
  - https://preview.aclanthology.org/setup/2025.coling-main.248
links:
  - affects: synopsis-llm-history
---
Song ほか（arXiv 2312.15156, 2023）: ChatGPT に指示だけで鍵語（keyphrase）を抜かせると、既存の教師なし・教師ありの手法にまだ大きく劣る。
Kang・Shin（COLING 2025, pp.3670–3686）: 指示の書き方 4 通り（素の指示・役割・候補を渡す・混合）を 6 つの標準データで比べ、Llama3-8B の素の指示が教師なしの PromptRank を上回った。
たぐりの「題材の言葉」（extract_theme_llm.py）は、この「指示だけで抜く」型。ただし学術の鍵語抽出は「本文中の語句をそのまま当てる」評価で、たぐりは「一般的な名詞に言い換えてよい」ので評価の物差しが違う。日本語・あらすじでの測定は見つけていない。要旨は検索結果の引用と抄録ページで見ただけで、本文は読んでいない。
