---
id: q-index-load-now
type: question
status: answered
date: 2026-10-16
title: 推薦の索引の初回（約 11 万書き込み）を、4 日待たずに早く入れるにはどうするか
sources:
  - cloudflare/scripts/deliver_catalogue.py
  - cloudflare/scripts/free_tier.py
  - https://github.com/island-6848/taguri-crawler/blob/main/.github/workflows/catalog.yml
links:
  - depends_on: dec-index-first-load
---
起案者「推薦の索引を今すぐ入れる方法を考えよう」（2026-10-16）。本番の推薦は索引が届くまで空のまま（q-interest-no-reco-prod）。

前提（コードで確かめた）:
- D1 の予算は UTC の 1 日ごと。deliver_catalogue.py は `min(WRITE_BUDGET 60,000, free_tier.d1_left)` を使い、d1_left は state ブランチの控え（free_tier.py の d1_writes、上限 CAPS 80,000）から引く。書く前に控えに足すので、同じ日に 2 回配っても合計は上限を越えない
- catalog.yml は concurrency group `catalog` で 2 本同時に走らない。手動実行（workflow_dispatch）の入力は mode（daily / weekly）だけ
- ここ（開発の箱）には Cloudflare の鍵がないので、D1 に入れるのは taguri-crawler の Actions からだけ

案:
- A. catalog.yml に「索引だけ」の手動実行を足す（取り直し・ポスター・過去の公演を飛ばし、前回の作業データから索引だけ作って差分を送る）。Actions は 1 回 5〜10 分見込み（月 1,500 分の上限に対し使用 650 分ほど）。その日の残りの予算をまるごと索引に使える
- B. 数日だけ過去の公演（past_stage、1 日約 2 万書き込み）を止め、その分を索引に回す
- C. 索引を小さくする（rec_stage 4,818 行は、これからの公演 1,335 件より多い。巡業の各会場・保存済みの束の公演が入っているはず。終わった公演を外せるか要確認）。題名の 2 文字の束（rec_gram 13,860 行）は既に最後に回してある

分からないこと: 4,818 行のうち終わった公演が何件か（作業データは state ブランチにあり、ここでは数えていない）。

答え（2026-10-16）: 案 A（索引だけの手動実行）を入れ、1.2 万行が入った〔index-only-run-1016〕〔dec-index-only-run〕。
