---
id: eval-favourite-kinds
type: finding
status: confirmed
date: 2026-10-14
title: 劇団・主催（監督の作品群で代用）と題材（ジャンルで代用）のお気に入りも、評価が無いうちの当たりを上げる
sources:
  - docs/research/person-reco-eval.md
  - tools/review/eval_favourite_seed.py
links:
  - supports: eval-favourite-seed
  - affects: comp-recommender
---
公開の映画評価データ（選ぶ 300 人と確かめる 500 人は別、2 抽出）。劇団・主催の代わりに監督の作品群、題材の代わりにジャンルをお気に入りにして、その作品を仮の評価として数えた。監督の作品群: 評価 0 件で +0.025 ±0.013 / +0.024 ±0.014、3 件で +0.014 / +0.010、10 件以降は差なし。ジャンル: 0 件で +0.031 ±0.011 / +0.024 ±0.010、3 件で +0.022 / +0.017、10 件で +0.010 / +0.007、20 件以降ほぼ差なし。ジャンルではお気に入りのジャンル自体の値も数えるほうがよかった。代わりのもので確かめた範囲で、劇団・題材そのものでは未確認。
