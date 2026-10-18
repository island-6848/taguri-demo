---
id: lit-llm-augmented-item-text
type: finding
status: unverified
date: 2026-10-18
title: LLM で品目の説明文を補ってから推薦に使うと精度が上がるという報告がある（LLM-Rec、KAR）。補った文が正しいとは限らない点も論文自身が扱っている
sources:
  - https://arxiv.org/abs/2307.15780
  - https://preview.aclanthology.org/dashboard/2024.findings-naacl.39
links:
  - affects: impl-theme-favourite
---
LLM-Rec（Lyu ほか, NAACL Findings 2024）: 品目の説明を LLM に 4 通りの指示で書き足させ、その文を使うと推薦が良くなる。単純な MLP でも複雑な内容ベースの手法と同等以上。補った情報が正しいとは限らないので、正解の情報を足した変形も試している。
KAR（Xi ほか 2023）は品目の事実の知識を LLM に作らせて推薦に混ぜる方法として LLM-Rec が紹介している（原論文は今回見ていない）。
たぐりは逆向きで、LLM に「足させない」（本文に無いものを落とす）。どちらが良いかは、外部の知識（評判）を持ち込まない方針〔lit-cold-start-dl〕と、出典を付けて理由を書く方針で決まっている。要旨は検索結果の引用と抄録ページで見ただけで、本文は読んでいない。
