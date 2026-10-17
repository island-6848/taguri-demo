---
id: dec-docs-refresh-1017
type: decision
status: adopted
date: 2026-10-17
title: 使い方ガイドとプレゼン資料を 10-17 の画面と推薦に合わせて直した。推薦の章は 3.1–3.13・式 1–16・図 1–9・参考文献 21 件の論文の形にした
sources:
  - docs/000003-final-presentation-taguri.html
  - docs/000010-user-guide-taguri.html
  - cloudflare/src/recommend.js
  - cloudflare/src/screens/recommend.js
links:
  - depends_on: dec-deck-algo-paper
  - depends_on: impl-interest-split
  - depends_on: dec-spread-and-partners
  - depends_on: dec-genre-axis
  - depends_on: dec-drop-venue-kind
  - depends_on: dec-source-kind-no-price
---
起案者の指示（2026-10-17）「使い方ガイド、プレゼン資料を今の内容に修正して。できるだけ文章ではなく図で表現。推薦アルゴリズムに関しては論文ぽく」。

プレゼン資料の推薦の章:
- 新しい節は 4 つ。3.5 種類のタグ（図 3）、3.8 興味あり・行けないを 1 公演ぶんに割って配る（式 10–11、図 6）、3.9 好きな人と組む人へ 1 段広げる（式 12、図 7）、3.10 一覧の並べ直しと外すもの（式 13、図 8、表）。
- 式 4 に興味ありの項 h_u を足した。裏の答え合わせの式は 14–16 に振り直した。図 1（全体の流れ）は描き直した。
- 図 6 の値は recommend.js の interestShares で出した（俳優 A 0.216 など）。
- 参考文献に [17]–[21] を足した。lit-content-overspecialization・lit-live-show-propagation・lit-topic-diversification・lit-popularity-bias・genre-25d-signals。
- 新しい部分の効き目は、舞台の実データで測っていない。試験で確かめたのは性質だけで、そのことを 3.13 に書いた。

プレゼン資料のほかの章:
- 2-3 の構成図を、Render・S3 から Cloudflare Workers・D1・R2・GitHub Actions・Firebase に描き直した。2-4 の設計判断もそれに合わせた。
- 2-2 の使い方と 2-1 の画面一覧を今の画面に合わせた。ログイン、4 つの答え、星 5 段階、＋、探す。
- 4 章の守りから、6 桁の連携コードと「永続保存は未完了」を外した。パスワードを預からないこと、回数と量の上限を足した。
- 5 章に 8（理由の ✕）と 9（日程と料金）を足した。

使い方ガイド:
- 2 章から 7 章を図で作り直した。ログイン、4 つの答え、理由の ✕、メニューの地図（ⓘ・＋・探す）、星 5 段階と評価しない、記録の足し方（＋・Google カレンダー・W キャスト）、データと安心、困ったとき。
