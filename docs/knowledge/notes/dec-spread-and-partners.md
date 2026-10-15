---
id: dec-spread-and-partners
type: decision
status: adopted
date: 2026-10-15
title: 同じ人ばかり出るのを和らげる: 1 ページ（15 件）に同じ人が筆頭の理由の公演は 2 件まで（並べ直し）、好きな人と同じ公演に関わる人へ 1 段だけ広げて新しい公演を弱く足す
sources:
  - cloudflare/src/recommend.js
  - cloudflare/src/screens/recommend.js
  - cloudflare/test/recommend-spread.test.js
links:
  - depends_on: lit-topic-diversification
  - depends_on: lit-popularity-bias
  - depends_on: lit-content-overspecialization
  - depends_on: lit-live-show-propagation
  - depends_on: lit-feedback-loop
  - affects: q-review-1015
---
起案者の指示（2026-10-15）「同じ人ばかり出るのを和らげる案も進めて」（docs/recommendation-concerns.md 4 章の 3、1 章の 1〜3）。
- 並べ直し（screens/recommend.js spreadLeads）: 点の順はそのままに、表示の 1 ページ（TOP＝15 件）ごとに、いちばん強い理由の人が同じ公演は LEAD_CAP＝2 件まで。越えた分は次のページへ回し、消さない。理由が種類だけの公演は数えない。都道府県で絞ったときも、この並びから選ぶ
- 1 段広げる（recommend.scoreFromIndex の expand、Python の参照には無いので一致試験の経路では動かない）: 値が正の人の上位 20 人が出るこれからの公演（60 件まで）の人物を読み、まだ値の無い人に「その公演でいちばん値の大きい好きな人の値 × 0.3」を仮に与え、その人の別の公演を候補にする。好きな人がすでに出ている公演には足さない（二重に数えない）。お気に入りの名前と、本人が「観た回に出ていなかった」と外した出演者（cast_off）は除く。理由には「（好きな○○と同じ公演に関わる人）」と出す
- D1 の読み: 推薦を計算し直すとき（控えが捨てられたとき）だけ、公演 60 件ぶんの人物と、広げた人の出演の行が増える。数は本番で測っていない（diag に入れていない）
- 値（2 件・0.3・20 人・60 件）は舞台のデータで確かめていない。広げる相手は「いま同じ公演に関わる人」で、過去の公演での共演の多さ（よく組む度合い）はまだ使っていない（過去の公演の人物を索引から引く仕組みが要る）
