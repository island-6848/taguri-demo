---
id: dec-deck-algo-paper
type: decision
status: adopted
date: 2026-10-14
title: 成果報告の資料の推薦の章を、論文の形（記法・番号付きの式・図・検証と限界・参考文献）に書き直した
sources:
  - docs/000003-final-presentation-taguri.html
  - cloudflare/src/recommend.js
  - cloudflare/src/reco-gate.js
links:
  - depends_on: dec-deck-algo-worker
  - depends_on: impl-person-ordinal-v3
  - depends_on: impl-hidden-gate
  - depends_on: eval-hidden-gate-sim
  - depends_on: eval-favourite-kinds
  - depends_on: dec-no-n1-evidence
  - depends_on: dec-recommend-weights-worker
  - depends_on: new-user-reco-threshold
---
起案者の指示（2026-10-14）「資料の推薦アルゴリズムのまとめはちゃんと論文ぽく数式とか使って根拠も示しながら書いて。ただし図にできるところは図にしながら」。

章の構成は次のとおり。
- 3.1–3.9：要旨、問題設定と記法、全体の流れ（図 1）、順序化（式 1–3、図 2）、縮約した値（式 4）、詳細の振り分け（式 5）、役職の重みと公演の点（式 6–7）、出す条件（式 8、図 3）、お気に入りの事前（式 9、図 4）、裏の答え合わせ（式 10–12、図 5）、計算の置き場所、検証と限界、変更点、参考文献 16 件。

式と図の作り方は次のとおり。
- 式は recommend.js・reco-gate.js の計算と同じ形にした（分母の κ、仮の評価が件数でなく重みに入ること、勝ち越しが最大の案を選ぶこと）。
- 式は MathML で書き、数式用のフォントとして Noto Sans Math を Google Fonts から読む。
- 本人の「効かせ方」（rank_weight、0/0.5/1/2/4）は、役職のまとまりごとの倍率 μ として、裏の答え合わせの倍率と掛け合わせる形で式に入れた（3a5f62c の rankedGroups）。推薦が出始める条件（結び付いた記録 2 件以上・評価 2 種類以上）は、式 3 の帰結として 3.3 に書いた。
- 図 2–5 は scratchpad の figs.py で SVG を作った。値は計算例と同じ（A の ◎ ＝ +1.212、例の公演の点 ＝ +0.383、W 14・L 4 で z ＝ 2.36）。

根拠の扱いは次のとおり。
- 根拠は lit-* のノートを [n] で引いた。原文を読めず要旨で確かめたものが多いことを、資料にも書いた。
- 持ち主 1 人の AUC は使わない（dec-no-n1-evidence）。数値は公開の映画データと、作った利用者でのものだけを載せ、舞台の実データでは未測定と明記した。
