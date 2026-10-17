---
id: lit-per-user-algorithm-selection
type: finding
status: unverified
date: 2026-10-17
title: 利用者ごとに推薦の手法を選ぶ研究は 2012 年からある（Ekstrand・Riedl RecSys 2012、Collins ほか 2018–2020）。効果は小さく、2026 年の監査では利用者ごとの重みに一貫した効き目は無かった
sources:
  - https://grouplens.org/recsys2012-error-analysis
  - https://arxiv.org/pdf/1805.12118
  - https://arxiv.org/pdf/2509.20134
  - https://arxiv.org/html/2608.05655
links:
  - affects: q-academic-novelty
  - affects: impl-hidden-gate
---
- Ekstrand & Riedl. When Recommenders Fail: Predicting Recommender Failure for Algorithm Selection and Combination. RecSys 2012。ある手法が外れる場面でも、別の手法が当てることが多い。二次資料によれば、利用者ごとに手法を選ぶ分類器（特徴は評価の数と評価のばらつき）は、全体で最良の 1 手法にわずかに及ばなかった。
- Collins ほか（arXiv 1805.12118 ほか）: 利用者ごと・1 件ごとの手法選び（meta-learning）。2020 年の報告では、それまでの利用者ごとの手法選びは成功していないとし、小さな改善（MAE 0.7107 対 0.7214）を報告。2025 年の arXiv 2509.20134 も、すべての利用者で最良の手法は無いことを示す。
- 2026 年の arXiv 2608.05655（Is Personalized Modality Weighting Actually Personalized?）: マルチモーダル推薦の「利用者ごとの重み」を監査し、利用者ごとにしても一貫した効き目は無かったと報告。
- たぐりの裏の答え合わせ（impl-hidden-gate）との関係: 利用者ごとに重み付けを選ぶ点は先行研究と同じ。違いは次の 3 つ。(1) 他の利用者を使わず本人の記録だけで決める。(2) 時間順に再生し、重ならない区切りで符号検定をする。(3) はっきり勝ったときだけ切り替え、既定に戻りやすくした。利用者ごとの選択は効き目が小さく、誤った切り替えが起きやすい、という先行の結果と整合する設計である。
- どれも検索結果の要約で見ただけ（arxiv.org はこの環境から開けない）。
