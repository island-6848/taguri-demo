---
id: lit-yahoo-multicriteria
type: finding
status: unverified
date: 2026-10-13
title: 観点ごとの評価がある公開データ（Yahoo! Movies：物語・演技・演出・映像＋総合）が研究で使われている
sources:
  - https://arxiv.org/pdf/2502.19271
links:
  - affects: q-aspect-attribution-check
---
多基準推薦の論文（arXiv 2502.19271 など）が、利用者 6,078 人・映画 976 本・評価 758,405 件のデータとして使っている。入手先（GitHub と書かれている）と利用条件は確かめられず、出演者・監督の情報があるかも分からない。観点ごとに下げる相手を変える案の検証に使えるかは未定。

2026-10-14 追記: GitHub に写しが 2 つある（KunalShm/Multi-Criteria-Recommendation-System の data_movies.txt＝13 段階の生の値、sydney-machine-learning/multicriteria-recommendersys の Movies_Yahoo.xlsx＝1〜5 に直した値で総合は項目の平均）。どちらも利用条件の記載が無く出どころも書かれていない。件数は 62,156 件（758,405 件は誤り）。映画 ID は番号だけで題名・出演者に結べない。手元の集計だけに使った（eval-yahoo-aspects）。
