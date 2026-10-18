---
id: dec-fav-over-interest
type: decision
status: adopted
date: 2026-10-18
title: 推薦の強さは お気に入り ＞ 興味あり。お気に入りから作る種の重さを 2 倍（FAV_SEED_W = 2）
sources:
  - cloudflare/src/recommend.js
  - tools/review/user_recommender.py
  - cloudflare/test/fav-over-interest.test.js
links:
  - depends_on: impl-interest-split
---
起案者の指示（2026-10-18）「推薦の強さ、お気に入り＞興味ありにしてほしい」。
- これまで: 興味ありは 1 公演ぶんの重さ（評価 1 件と同じ w）を、その公演の人・種類に割って配る。お気に入りは、登録した名前の公演（種）にいる人それぞれへ w を足す。ただし登録した名前そのものは数えない（その名前の公演はお気に入りの画面に出すので、おすすめからは外している）。そのため、登録した名前と組む人への効き方が、興味ありより弱く見えることがあった
- いま: 種から足す重さを w × FAV_SEED_W（2）にした。同じ形の 1 公演どうしなら、お気に入りから来た人の値が興味ありから来た人の値より大きくなる（試験 fav-over-interest）。Python の user_recommender.person_values も同じにした（Worker と値を一致させる約束）。版 screen-v22 で計算し直す
- 分からないこと: 2 倍が本番でちょうどよいか（実データで測っていない。real-data-eval-plan で確かめる）
