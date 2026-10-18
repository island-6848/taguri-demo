---
id: dec-aspects-five-levels
type: decision
status: adopted
date: 2026-10-18
title: 評価の詳細を 5 段階にし、項目ごとの ✕ で「この作品には無い」にできる（無い項目は表示と推薦から外す）。前の 3 段階はそのまま読み、移行は要らない
sources:
  - cloudflare/src/recommend.js
  - cloudflare/src/screens/rate.js
  - tools/review/user_recommender.py
  - tools/review/rate_performances.py
  - web/app.js
  - web/theme.css
  - cloudflare/test/screens/scenarios.json
  - cloudflare/test/test_recommend_index.py
  - tools/taguri/test_user_recommendation.py
  - cloudflare/test/e2e-walk.js
links:
  - affects: dec-aspects-screen
  - affects: impl-rating-aspects
  - affects: comp-recommender
  - depends_on: lit-rating-scale-points
  - raises: q-aspect-levels-check
---
起案者の指示（2026-10-18）「評価の詳細、今3段階で設定してるけど適切？最低限5段階くらいほしい。あと作品によっては歌ダンスがないこともあるので、なかったときは✕で要素を消せるようにしてほしい。」

「3 段階は適切？」への答え: 詳細は「気になった ↔ 良かった」の両方向の尺度で、評価尺度の研究では 2〜4 段階は 5〜7 段階より回答の信頼性・妥当性が低いと報告されている〔lit-rating-scale-points、原典は未確認で unverified〕。3 段階では「少し気になった」と「ひどかった」を分けられない。両方向の尺度で勧められるのは 7 段階だが、項目が 8 つあり電話でつまみを動かすので、起案者の言う最低限の 5 段階にした。

決めたこと:
- 段階: とても気になった（−2）・気になった（−1）・ふつう（0）・良かった（1）・とても良かった（2）。つまみ（range、−2〜2）で選び、言葉を右に出す
- 保存の形（works.aspects・records.aspects、カンマ区切り）: "--code" とても気になった、"code" 気になった、"+code" 良かった、"++code" とても良かった、"~code" この作品には無い。ふつうは書かない。並びは 気になった・良かった・とても気になった・とても良かった・無い の順、その中は項目の順（recommend.ASPECT_MARKS・user_recommender.ASPECT_MARKS）。1 つの項目に印 2 つ・知らない印は断る（「1 つの項目に印が 2 つ付いている」）
- 前の 3 段階: "+code"・"code" は同じ言葉の 良かった（1）・気になった（−1）として読む。言葉が変わらないので、前に付けた人の記録の意味が変わらない。保存の形もそのまま正しい形なので、移行（0037 以降）は作らない（記録を書き換えない）
- 推薦（user_recommender.aspect_share と recommend.js の同じ関数）: 項目の効き方を、その記録で最も強い印に対する強さで割り引く（とても良かった の横の 良かった は半分）。印の強さがそろっている記録（3 段階の記録はすべて）は前と同じ点になる。作品全体の良し悪しは評価（星）そのものが持つので、「とても」は どの人のおかげ・せいか の配分にだけ使う。Python と Worker の一致は test_recommend_index.py（5 段階と無いを混ぜた作り物の記録）で確かめた
- この作品には無い: 項目の行の右の ✕ で外す。外した項目は行を隠して下に「＋ 歌・音楽」のように並べ、押すともう一度足せる（ふつうから）。要約（見出しの横）にも出さない。推薦では印の無い項目と同じに扱い、効き方の計算に入れない
- 無料枠: 1 回の保存は前と同じ UPDATE 1 行。読み書きの回数は増えない

確かめたこと: Python と Worker の画面の一致（scenarios の「rating aspects」に 5 段階・無い・断る場合を足した）、Python の単体（5 段階の読み、無い項目が点を変えない、強い印の横の弱い印が半分）、e2e-walk の「詳細を 5 段階で付け、無い項目を ✕ で外して戻す」（パソコンと 375px の写し）。

2026-10-18 追記: 同じ日の起案者の指示で、言葉を 好みではない／やや好みではない／ふつう／やや好き／好き に替え、推薦は「最も強い印に対する強さで割る」配分をやめて ±2 をその項目の役職に 1.5 倍効かせる形にした〔dec-aspects-strong-weight〕。保存の形・「この作品には無い」・移行なしは変わらない。
