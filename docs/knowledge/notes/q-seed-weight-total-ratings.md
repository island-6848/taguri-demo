---
id: q-seed-weight-total-ratings
type: question
status: open
date: 2026-10-18
title: お気に入り・興味ありの仮の好みの重み 3/(3+評価の数) は、その人に関係の無い評価が増えるだけで薄まる（関係の無い 3/5 を 100 件で約 95% 減）。人・種類ごとの証拠の量で薄めるほうがよいか（#107、測ってから）
sources:
  - https://github.com/island-6848/taguri-demo/issues/107
  - cloudflare/src/recommend.js
  - tools/review/user_recommender.py
links:
  - depends_on: eval-favourite-seed
  - depends_on: dec-fav-over-interest
---
- 測ること: 候補とお気に入りを固定し、関係の無い評価だけを足したとき、お気に入りの周りの公演が上位から消える件数。全履歴の数で薄める（いま）と、その人・種類に付いた評価の数（n）で薄める案を、公開の映画評価データの再現（eval_favourite_seed.py、〔eval-favourite-seed〕）と手元の再生（H1）で比べる
- 注意: 薄め方は Python（user_recommender.person_values）と JS で同じにする必要がある（一致の試験 144+24 通り）。FAV_SEED_W = 2（お気に入り＞興味あり、〔dec-fav-over-interest〕）は変えない
