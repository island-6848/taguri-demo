---
id: dec-deck-algo-worker
type: decision
status: adopted
date: 2026-10-14
title: 成果報告の資料の推薦の章を、本番の Worker の計算（person-ordinal-v3+fav3+asp1+tour1+why1）に合わせて書き直した
sources:
  - docs/000003-final-presentation-taguri.html
  - cloudflare/src/recommend.js
  - cloudflare/src/reco-gate.js
  - cloudflare/src/screens/recommend.js
links:
  - depends_on: impl-person-ordinal-v3
  - depends_on: impl-favourite-seed
  - depends_on: impl-hidden-gate
  - depends_on: dec-account-cap-counted
---
起案者の指示（2026-10-14）「現在の推薦アルゴリズムをまとめて、プレゼン資料を更新して」。
- 3 章を 3-1〜3-7 に書き直した: 全体の流れ（図）、評価を本人の中での順位として読む（z の式と計算例）、公演の点（人物の値 Σz÷(n+3)・役職の重み・上げる 3 人＋下げる 3 人＋種類の平均・理由を言える公演だけ）、詳細とお気に入り（asp1・fav3）、裏の答え合わせ、どこで計算しているか、以前の仕組みからの変更と未確認のこと
- 計算例の値は recommend.js の personValues で出した（評価 10 件の人で ◎＋1.212・○ 0・△−1.039・×−1.559、例の公演 0.383）
- 5 章の古い記述（公開先が Render・永続保存が未検証・網 C・あらすじの点が未導入）も今に合わせた
- 舞台の実データでの当てやすさは測っていないことを、資料にそのまま書いた
