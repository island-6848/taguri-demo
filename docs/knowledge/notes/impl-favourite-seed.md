---
id: impl-favourite-seed
type: finding
status: confirmed
date: 2026-10-13
title: 評価が無いうちの推薦をお気に入りから作るようにした（person-ordinal-v3+fav1、Worker）
sources:
  - tools/review/user_recommender.py
  - cloudflare/scripts/build_recommend_index.py
  - cloudflare/src/recommend.js
  - cloudflare/src/worker.js
links:
  - answers: q-favourites-seed
  - depends_on: eval-favourite-seed
  - depends_on: impl-person-ordinal-v3
  - depends_on: eval-favourite-kinds
  - affects: comp-recommender
---
お気に入りのうち種類が「人」「原作者」のもの（最大20人）が、出演・演出・脚本・作・原作・翻訳・潤色・構成・振付・作曲・音楽のどれかで関わる候補の公演（公演IDの順に最大60）を、その公演の人物と種類のタグごとに仮の評価 z = 0.4√12、重み 3 /（3 + 本人の評価の数）で足す。人物の値の分母に重みが入り、関わった数 n には入れない（n は本人の評価の数のまま）。お気に入り本人の値は足さず、その人の公演（種の公演）は推薦から外す。Python の参照実装（score_from_index・seeds_from_favourites）と Worker が同じ点を出すことを一致テストで確かめた。お気に入りを足し外しすると保存した推薦を捨てる。「団体」「主催」「作品」「題材」のお気に入りはまだ使っていない（索引に団体名から引く表が無い）。Render の Python 版の推薦は変えていない。

2026-10-14 追記（+fav2）: 団体・主催は公演団体名（正規化した rec_stage.gkey）に名前を含む公演、作品は題名（tkey）に名前を含む公演も種にした（照合の規則は recommend2.declared_hits と同じ）。Worker は版の公演を 1 回なめる問い合わせで引く。題材はあらすじの題材が索引に無いので未対応（q-theme-favourite）。
