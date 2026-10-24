---
id: f-reco-recompute-cpu-1021
type: finding
status: confirmed
date: 2026-10-21
title: 本番の大きさの索引で、おすすめの計算し直しは評価 10 件で 17 ms・40 件で 37 ms・100 件で 59 ms（無料は 10 ms）。裏の答え合わせを外しても 10 ms には届かない
sources:
  - cloudflare/src/recommend.js
  - cloudflare/src/reco-gate.js
  - cloudflare/src/screens/recommend.js
links:
  - depends_on: q-reco-cpu-structure
  - depends_on: workers-free-cpu-10ms
---
もう一つのセッションの知らせ（おすすめの計算し直し約 70 ms。ブランチ claude/demo-records-setup-yqo65u の f-reminder-cpu-1021）を受けて、同じ手順で測り直した。taguri-crawler の state ブランチ（2026-10-21 時点）から master の build_recommend_index.py で索引を作った（rec_stage 5,122・クレジット 28,710・人 16,064）。過去の公演は replay_job.past_sql で作った（17,802 行）。手元の Worker（harness の setup）で、架空の利用者に評価 N 件・興味あり 15 件を付けた。評価を 1 件付け替えるたびに /api/screen/recommend を呼び、かかった時間から D1（SQLite）の待ちを引いた（7 回の中央値。スクリプトは scratchpad にだけ置いた）。

- 計算し直し: 評価 10 件 17 ms（15〜27）、40 件 37 ms（32〜112）、100 件 59 ms（40〜90）。控えに当たれば 4 ms 前後
- 内訳（評価 40 件、node --cpu-prof の関数ごとの時間を 1 回あたりに割った目安）:
  - 裏の答え合わせ（reco-gate.chooseVariant）約 8 ms
  - 点数付け（scoreFromIndex の自分の分）約 6 ms
  - 束ね（rankedGroups の自分の分）約 5 ms
  - personValues 約 4 ms
  - 同じ作品の判定（sameProduction）約 3.5 ms
  - 所属から広げる・人の名前など 数 ms
- 読み: どれか 1 つを外しても 10 ms には届かない（裏の答え合わせを外しても約 30 ms）。計算の置き場所を変える（前もって計算する・数回に分ける）必要がある
- この機械と Cloudflare では速さが違うので目安。試験の SQLite には D1 の raw() が無く、行を配列にする分が少し多く出ている
