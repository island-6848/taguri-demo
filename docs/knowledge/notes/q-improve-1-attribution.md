---
id: q-improve-1-attribution
type: question
status: open
date: 2026-10-20
title: 改善案 ①「評価を人物ごとに適切に割り当てる」── 何が既にあり、何が残っているか。どれを直すか
sources:
  - tools/review/user_recommender.py
  - cloudflare/src/recommend.js
links:
  - depends_on: impl-rating-aspects
  - depends_on: eval-yahoo-aspects
  - depends_on: q-aspect-attribution-check
  - depends_on: q-aspect-usage-check
  - depends_on: dec-part-two-tiers
---
起案者が渡した改善案の文書（taguri_recommendation_improvements.md、2026-10-20）の ① を、コードとナレッジに照らして検討した。起案者の指示は「検討→修正。いきなり実装しない」。

既にあるもの（コードで確かめた）:
- 総合の星のあとに、任意で 8 項目×5 段階（好みではない〜好き）と「この作品には無い」を付けられる〔impl-rating-aspects〕〔dec-aspects-five-levels〕。改善案の「総合＋任意の項目」はほぼこの形
- 付いた記録では、項目→役職の割合 α で評価の届き方を変える（式 5、user_recommender.aspect_share と recommend.js aspectShare は同じ）。±2 は 1.5 倍〔dec-aspects-strong-weight〕

残っている点:
1. 項目を付けない記録は、関わった全員に同じ z が届く（a ＝ 1）。改善案の指摘どおり
2. 項目を付けた記録で割合が 0 の役職（例: 「演技が好き」の記録の脚本家）は、分子に 0、分母に 1 が足される（person_values の tally[key][2] += 1.0、recommend.js 345 行）。つまり「ふつう（z ＝ 0）の評価が 1 件」と同じに数えられ、その人の値が 0 へ引かれる。「その記録はその人について何も言っていない」とみなすなら、分母にも割合を掛ける形がある。どちらが正しいかは決めていない
3. 項目がどれだけ付けられているかは、本番の D1（works.aspects）を見ないと分からない。この環境からは読めない〔q-aspect-usage-check〕

材料:
- Yahoo! Movies の項目別評価では、27% の評価で項目が総合から 1 段以上ずれる。ただし項目の重みを人ごとに学んでも総合は当たらなかった〔eval-yahoo-aspects〕。ずれはあるが、項目を細かく取れば当たるとは言えない
- 作ったデータでは、項目を仮定どおりに付ける人には効き、でたらめに付ける人には害がある〔eval-aspects-sim〕
- 項目なしの評価に役の格（主役を重く）で既定の割合を付ける案は、「◎ も主役が良かったからとは限らない」で取り下げ済み〔dec-part-two-tiers〕

次に決めること: 起案者との検討で、(A) 測るだけ (B) 分母の扱い (C) 入力を増やす画面の工夫 (D) 既定の割合 のどれを、どの順で進めるか。
