---
id: dec-aspects-strong-weight
type: decision
status: adopted
date: 2026-10-18
title: 詳細の言葉を 好みではない〜好き の 5 段階に替え、好き・好みではない（±2）はその項目の役職の人に 1.5 倍効かせる（±1 だけの記録は前と同じ点）
sources:
  - tools/review/user_recommender.py
  - cloudflare/src/recommend.js
  - web/app.js
  - tools/taguri/test_user_recommendation.py
  - cloudflare/test/test_recommend_index.py
  - cloudflare/test/e2e-walk.js
links:
  - answers: q-aspect-levels-check
  - affects: dec-aspects-five-levels
  - affects: impl-rating-aspects
  - affects: comp-recommender
  - raises: q-aspect-usage-check
---
起案者の指示（2026-10-18）「評価の詳細を 5 段階（好みではない〜好き）に変えて」「詳細評価のとてもを推薦の効き方も強めてほしい。該当する人をちょっと重くするとか。」

決めたこと:
- 言葉: つまみ −2〜2 の順に 好みではない／やや好みではない／ふつう／やや好き／好き。保存の形（"--code" "code" "+code" "++code" "~code"）は変えない。前の 3 段階の "+code"・"code"（良かった・気になった）は やや好き・やや好みではない として読む。見出しの要約は「好き: 演技・出演／やや好みではない: 値段」の形（好き → 好みではない の順、ふつう・無い項目は出さない）
- 推薦（user_recommender.aspect_share と recommend.js の aspectShare、定数 ASPECT_STRONG = 1.5）: ±2 の項目が指す役職の割合を 1.5 倍にする（割合は 1 を越えてよい。例: 演技が「好き」なら出演者に評価の 1.5 倍、演出家に 0.3 倍）。反対側の項目が引く分も ±2 なら 1.5 倍にし、多くても全部まで（符号は変えない）
- 前の形（その記録で最も強い印に対する強さで割る配分）はやめた。理由: 割る形では印が 1 項目だけのとき「好き」と「やや好き」が同じ点になり、起案者の言う「該当する人をちょっと重く」にならない。割ったうえで上乗せする形は、±2 の横の ±1 が下がる（±1 だけの記録との釣り合いが変わる）うえに説明が 2 段になる。上乗せだけなら ±1 の効き方はどの記録でも同じで、±2 だけが少し重い
- ±1 だけの記録（前の 3 段階の記録すべて）は前と同じ点（倍率 1.0 で、掛け算の順も同じ）。Python と Worker の一致は test_recommend_index.py、±1 だけの記録の割合が前と同じことは test_user_recommendation.py で確かめた
- 1.5 は「ちょっと」の仮の値。本人の後の評価を当てるかは、記録が溜まってから確かめる〔q-aspect-usage-check〕
