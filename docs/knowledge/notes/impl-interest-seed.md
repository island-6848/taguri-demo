---
id: impl-interest-seed
type: decision
status: superseded
date: 2026-10-15
title: 興味ありを押した公演を、お気に入りと同じ重みの仮の ◎ として推薦に入れた（新しい順に 60 件まで、一覧にしかない公演は出演欄から人物を読む）
sources:
  - cloudflare/src/screens/recommend.js
  - cloudflare/test/recommend-screen.test.js
links:
  - answers: q-interest-seed
  - depends_on: interest-not-in-v3
  - depends_on: impl-favourite-seed
---
起案者の指示（2026-10-15）「一回その案にしてみて」。screens/recommend.js の interestSeeds が、reaction を公演ごとに新しい答えで上書きし（日ごとの行なので）、いま興味ありの公演を新しい順に MAX_SEED_STAGES（60）まで選ぶ。人物は索引（rec_people・past_stage）から、無ければ一覧（catalogue）の出演欄を parseCredits で読む。お気に入りの種と合わせて personValues に渡すので、重みは同じ z = 0.4√12・3/(3+評価の数)。理由の作品名には押した公演の題名が出る（印の順は ◎○△× の後）。画面の控えの印を screen-v3 にした。
- 試験: 観た記録の無いアカウントが、一覧にだけある公演で興味ありを押すと、同じ俳優の公演が推薦に出る。後で興味なしに変えると消える
- 仮の ◎ だけで上がった人の理由が「（履歴 0 本）」と出ていた（お気に入りの種でも同じ）。「（お気に入り・興味ありの公演から）」に直した
- 確かめていないこと: 本番の索引での CPU 時間（種が最大 120 公演に増える。q-real-catalog-stats）、偏り（lit-feedback-loop）。旧い /migration-api の推薦（worker.js computeRecommendations）には入れていない
- 成果報告の資料（docs/000003）の推薦の章はまだ書き換えていない
