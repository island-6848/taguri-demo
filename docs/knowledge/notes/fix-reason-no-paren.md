---
id: fix-reason-no-paren
type: finding
status: confirmed
date: 2026-10-18
title: 括弧の説明の無い理由の行は、推薦アルゴリズム（順位）の問題ではなく、理由の文を作る側の問題。評価の無い人・形式（興味あり・お気に入りの公演だけで上がったもの）で、作品名がこのカードの公演そのものしか無い・引けないと、名前だけの行になっていた
sources:
  - cloudflare/src/screens/recommend.js
  - tools/review/render_recommend.py
  - cloudflare/test/fav-reco.test.js
  - cloudflare/test/recommend-screen.test.js
  - tools/review/test_reason_works.py
links:
  - affects: dec-reason-two-works
  - affects: dec-reason-work-titles
---
起案者の問い（2026-10-18）「括弧でおすすめ理由がついてないものがおすすめ理由に出ちゃってる。なぜ？推薦アルゴリズムの問題？」

調べたこと（リポジトリのコード・試験）:
- 理由の行の括弧は screens/recommend.js の worksText が作る。作品名があれば「（『A』・『B』）」、無ければ評価の本数で「（履歴 n 本）」、本数も 0 なら空（2026-10-18 の指示で「履歴 0 本」「（お気に入り・興味ありの公演から）」と書くのをやめたため）
- 本数が 0 になるのは、評価した公演には出ておらず、興味あり・お気に入りの公演だけで上がった人・形式。その人の作品名は興味あり・お気に入りの公演の題名から引く（personTitles）
- 作品名が空になる場面が 2 つある
  1. カードを作るとき（cardsHtml）、作品名からこのカードの公演そのものの題名を除く。同じ公演が別の番号（会場・ツアーの鍵の違い）でお気に入り・興味ありの側にあると、その人・形式の作品名はこの公演だけなので、除くと空になる
  2. 興味あり・お気に入りの公演の題名を、公演の一覧（rec_stage・catalogue）から引けない（終わって一覧から外れた公演。名簿 rec_people には過去の公演も残る）
- 前の試験（recommend-screen.test.js）は、この名前だけの行（「脚本 家丁」）を出すことを期待していた
- 順位の計算（scoreFromIndex）は、その人・形式の値で正しく上げている。理由の文が説明を書けなかっただけで、推薦アルゴリズムの誤りではない。ただし 1. は「同じ公演を別の番号で推している」ことでもあり、同じ公演の束ね（sameProduction）は答えた公演しか見ていない（お気に入りの一覧の公演は見ていない）

直したこと: 括弧の説明（作品名・履歴の本数・好きな人・お気に入りの名前）を書けない行は理由に出さない（Worker の reasonRows と Python の reason_rows の両方。形式の行も同じ）。全部の行が消えたカードは「理由を出せていません」になる。

分からないこと: 本番で 1. と 2. のどちらが多いか（本番の D1 は見ていない）。1. を減らすには、お気に入りの一覧に出る公演と同じ公演も sameProduction で外すとよいかもしれない（q-fav-same-production）。
