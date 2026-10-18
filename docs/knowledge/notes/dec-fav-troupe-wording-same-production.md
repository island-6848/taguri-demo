---
id: dec-fav-troupe-wording-same-production
type: decision
status: adopted
date: 2026-10-18
title: 団体で登録したお気に入りの理由は「劇団乙の『舞台ふたつめ』出演」（主催と書かない）。お気に入りの一覧に出る公演と同じ公演（別の番号）はおすすめから外す
sources:
  - cloudflare/src/screens/recommend.js
  - cloudflare/test/fav-reco.test.js
links:
  - answers: q-fav-same-production
  - depends_on: fix-fav-reason-roles
---
起案者の答え（2026-10-18）「団体は必ずしも主催じゃない。文言を変えて。おすすめから外して」。

- 〔fix-fav-reason-roles〕で団体・主催の登録名に「主催」と書いていたのをやめ、「（劇団乙の『舞台ふたつめ』出演）」の形にした（favDetails は団体・主催・作品・題材に役職を付けない。favText は団体・主催の名前の後ろに「の」を付ける）。
- 〔q-fav-same-production〕: おすすめの束をまとめる sameProduction に、答えた公演に加えてお気に入りの一覧に出る公演（nameHits の hits）を多くて 120 件渡し、同じ公演（同じ題名で、団体が同じか片方に無い・会場が同じ・作り手に同じ人がいる）は出さない。D1 の読み取りは、おすすめの控え（rec_cache）を作り直すときに rec_stage の主キーの行が多くて 120 行増えるだけ。
- 理由の控えの版は screen-v37。
- 本番でどれだけ外れるかは測っていない。
