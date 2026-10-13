---
id: lit-cold-start-dl
type: finding
status: unverified
date: 2026-10-13
title: 新作向けの深層学習の推薦（DropoutNet・CB2CF・two-tower・言語モデル）は、対象分野の協調データか外部への送信が要り、たぐりの方針にそのままは合わない
sources:
  - https://arxiv.org/abs/2305.06474
  - https://arxiv.org/abs/2305.08845
  - https://arxiv.org/abs/1908.10084
links:
  - affects: comp-recommender
---
docs/research/reco-without-reputation.md 第 3 節（要旨・二次資料の範囲）。DropoutNet・CB2CF・LightFM は観劇の利用者データで学ぶ埋め込みが要る。two-tower は作品側を公開データ、利用者側を本人の小さな回帰にすれば合う。文章の埋め込み（Sentence-BERT・Ruri）は公開のあらすじだけで作れるので合うが未検証。ゼロショットの言語モデルは普通の推薦に負ける報告（Kang 2023）、並べる順で結果が変わる（Hou 2023）、評判の知識を持ち込む。微調整（TALLRec・P5）は無料枠では不可。
