---
id: q-fav-reco-running-shows
type: question
status: open
date: 2026-10-18
title: お気に入りの共演者などの別の公演が、終わった・もう始まっている・本人の公演だけのとき、おすすめは 0 件のまま。始まっている公演も出すか、案内の文を実際に合わせるか
sources:
  - cloudflare/src/recommend.js
  - cloudflare/src/screens/recommend.js
  - cloudflare/test/fav-reco.test.js
links:
  - depends_on: fix-fav-only-no-reco
---
〔fix-fav-only-no-reco〕の (3)。おすすめの候補は「まだ始まっていない公演」だけ（scoreFromIndex の already running）。お気に入りの名前の共演者・作り手の別の公演が、どれも始まっている・終わっている・登録した本人の公演（お気に入りの一覧に出す）だと 0 件で、初めての人の案内（TIPS の 2）が出たままになる。

案（起案者に決めてもらう）:
- A: 始まっている公演も、千秋楽まで日があればお気に入りだけの人には出す（いまの「始まっていない公演だけ」の約束を変える）
- B: 案内の文を実際に合わせる。例「共演者や題材などが推薦に反映されます（関わりのある人のこれからの公演が見つからないときは、まだ出ないことがあります）」
- C: お気に入りを登録しているのに 0 件のときだけ、一文添える（例「お気に入りの○○と関わりのある人の、これからの公演がまだ見つかっていません」）

本番の索引で、お気に入りだけの人のうち何割がこれに当たるかは測っていない。
