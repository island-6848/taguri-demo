---
id: dec-reading-share-6-4
type: decision
status: adopted
date: 2026-10-20
title: 朗読劇とほかの形式を兼ねる公演は、形式の札を朗読劇 0.6・ほかの形式 0.4（ほかが 2 つ以上なら残りを等分）の重さで数える。評価から学ぶ側とこれからの公演の点の両方
sources:
  - tools/review/user_recommender.py
  - cloudflare/src/recommend.js
  - cloudflare/scripts/build_recommend_index.py
  - cloudflare/test/pieces.test.js
  - cloudflare/test/test_recommend_index.py
links:
  - depends_on: dec-reading-dual-form
---
起案者の指示（2026-10-20）「この場合はリーディングのほうが若干つよいことが多い。リーディング音楽劇は朗読劇6音楽劇4くらいだった」。

- user_recommender.kind_shares / recommend.kindShares（READING_SHARE = 0.6）。1 公演の #形式 の札が 2 つ以上で朗読劇を含むときだけ働き、合わせて 1（札 1 つの公演と同じ重さ）
- 評価から学ぶ側（person_values / personValues）: その公演の評価 z を、朗読劇には ×0.6、ほかの形式には ×0.4 の重みで平均に入れる（作品ごとに分けた記録も同じ）
- これからの公演の点（build_recommend_index の rec_credit.role_w）: 札の重さ GENRE_W × 0.6 / × 0.4
- 札が 1 つの公演・兼ねていない公演は 1.0 を掛けるだけで、前と同じ値（Python との一致試験はそのまま通る）
- 「リーディングミュージカル」（ミュージカル・朗読劇）も同じ 6:4（起案者の確認 2026-10-20「リーディングミュージカルも6:4でいい」）
- 本番に出るのは次の取得で推薦の索引を作り直してから（学ぶ側は配布してすぐ）
