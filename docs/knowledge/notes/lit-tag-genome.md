---
id: lit-tag-genome
type: finding
status: unverified
date: 2026-10-18
title: 映画の「タグゲノム」は、1,128 個のタグについて全作品に 0〜1 の関連度を持たせ、利用者の調査で学習・評価した（Vig・Sen・Riedl 2012）
sources:
  - https://files.grouplens.org/datasets/movielens/ml-25m-README.html
  - https://grouplens.org/datasets/movielens/tag-genome-2021/
links:
  - affects: impl-theme-favourite
  - affects: theme-words-sparse-past
---
Vig・Sen・Riedl, ACM TiiS 2(3), 2012, DOI 10.1145/2362394.2362395。MovieLens の README によれば、タグ・評価・レビューから機械学習で関連度を計算し、9,734 作品 × 1,128 タグの密な表にした。2021 年版で改良（Kotkov ほか 2021）。
たぐりとの違い: たぐりの #題材 は「ある・ない」の 2 値で、1 公演 6 語まで。そのため評価した公演との重なりが少ない〔theme-words-sparse-past〕。関連度を連続値で持てば重なりは増えるが、学習に使う多人数の判断がたぐりには無い。
論文の本文は読んでいない。数字はデータセットの README（GroupLens の一次資料）による。
