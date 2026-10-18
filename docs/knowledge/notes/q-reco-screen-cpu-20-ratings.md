---
id: q-reco-screen-cpu-20-ratings
type: question
status: open
date: 2026-10-18
title: 今週のおすすめの計算（rankedGroups）を、試験の小さな索引で measure_worker.mjs に通すと、評価 20 件以上で JS の CPU の中央値が 10 ミリ秒を越えた。本物の索引・本物の Worker でどうか
sources:
  - cloudflare/scripts/measure_worker.mjs
  - cloudflare/src/screens/recommend.js
  - cloudflare/src/reco-gate.js
links:
  - depends_on: workers-free-cpu-10ms
  - affects: fix-api-recommend-delegates
---
2026-10-18、#119 で measure_worker.mjs を画面と同じ道（works・rankedGroups）に向けたあと、この作業の環境で試験の索引（parity_fixture の 1 つ目、公演 74・クレジット 675）に通した結果（2 回）: 評価 0 件で 5.4〜5.7 ms、5 件で 6.6〜7.2 ms、20 件で 12.8〜13.9 ms、50 件で 15.4 ms（SQLite の時間は除いた中央値、最大はその 2〜3 倍）。
- これは画面がもともと払っている計算の重さで、#119 で増やしたものではない（/api/recommend は画面の控えを読むだけになり、前のように控えを上書きして計算し直させることは無くなった）
- 見立て（未確認）: 評価が MIN_HISTORY（5）を越えると、裏の答え合わせ（chooseVariant）が区切りごとに personValues を計算し直すので、評価の数とともに増える。手元の機械は Workers と違うので、そのまま比べられない
- 調べること: 取得の環境で本物の索引に measure_worker.mjs を通す。越えるなら、どこが重いか（chooseVariant・sameProduction・控えの JSON）を分けて測る。10 ミリ秒の上限は〔workers-free-cpu-10ms〕
