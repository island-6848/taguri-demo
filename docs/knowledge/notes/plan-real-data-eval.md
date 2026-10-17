---
id: plan-real-data-eval
type: decision
status: adopted
date: 2026-10-17
title: 推薦の効き目を本番の利用者のデータで測る設計。主な方法はバックアップを手元で再生する方法で、開幕リマインドでの答えを偏りの少ない主な結果にする。足す記録は答えの行の列と、1 人 1 日 1 行だけ
sources:
  - docs/research/real-data-eval-plan.md
links:
  - depends_on: q-academic-novelty
  - depends_on: dec-no-n1-evidence
  - depends_on: dec-d1-backup
  - depends_on: lit-mnar
  - depends_on: impl-hidden-gate
---
起案者の指示（2026-10-17）「実データで測る方法を設計して」。中身は docs/research/real-data-eval-plan.md にある。

- 仮説は H1–H5 で、見る前に決めた。
  - H1：答えの AUC。
  - H2：おすすめと開幕リマインドの当たる割合の比較。
  - H3：観る前の点と、観たあとの評価。
  - H4：初日より前に知らされたか。
  - H5：部品を 1 つずつ外した計算との比較（Holm の補正）。
- 主な方法 A：D1 の毎日のバックアップを手元で復号し、時間順に再生する。Worker の JS で、日 t より前の記録だけから計算し、t より後の答えを当てる。費用はゼロ。
- 偏りへの手当て：開幕リマインドは点と関係なく全部の公演を出す。そこでの答えを主な結果にし、おすすめ・探すでの答えは参考にとどめる。
- 方法 B：1 つの一覧に 2 つの並べ方を交互に混ぜる（interleaving）。任意で、CPU を測ってから決める。
- 足す記録は 2 つ。
  - reaction の列（rank・score・ver・arm）。答えを書く行に入れるので、書き込みは増えない。
  - rec_shown（1 人 1 日 1 行・180 日で消す）。
- 人数の目安：H5 で AUC の差 0.05 を見分けるには、約 30 人。
- 始める前に、規約に分析の目的を書き、分析から外れる設定を置く。
