---
id: d1-index-measure-193
type: finding
status: confirmed
date: 2026-10-18
title: sessions の user_id・rec_stage と rec_card の tour をひく文は索引が無く、手元の D1 で 1 回 1,558〜5,706 行（空のアカウントの片付けは 30 万行）を読んでいた。0038 の 3 つの索引で 8〜499 行になり、書き込みは足した・upsert した行ごとに 1 増える
sources:
  - https://github.com/island-6848/taguri-demo/issues/193
  - cloudflare/migrations/0038.sql
  - cloudflare/test/indexes.test.js
  - cloudflare/scripts/deliver_catalogue.py
links:
  - depends_on: d1-upsert-counts
  - affects: dec-recommend-worker-cards
---
issue #193 の候補の索引を測った。全 migration（0001〜0036）を当てた手元の D1（wrangler の getPlatformProxy。workerd の SQLite が返す meta.rows_read・rows_written）に、本番の大きさの作り物の行（利用者 300 人 × 10 端末、rec_stage 4,818 行、rec_card 1,557 行。行数は d1-upsert-counts・dec-index-first-load の記録から）を入れた。

| 文 | 索引なしの計画 | rows_read 前 → 後 |
|---|---|---|
| startSession の端末数の DELETE（worker.js） | SCAN sessions | 5,706 → 31 |
| DELETE sessions WHERE user_id（worker.js） | SCAN sessions | 3,009 → 21 |
| 端末数（screens/account.js） | expires_at の索引で範囲 | 2,093 → 8 |
| 空のアカウントの片付け（cleanup.js、1 日 1 回）の sessions の部分 | 利用者ごとに SCAN s | 307,172 → 499 |
| rec_stage tour IN 20 件（recommend.js・search.js） | ver だけの SEARCH | 4,818 → 88 |
| rec_card tour IN 20 件（lists.js buckets、日記帳・カレンダー・検索・リマインド） | ver だけの SEARCH | 1,558 → 89 |
| その日の新規登録数（rate-limit.js） | SCAN users | 300（足さない） |

書き込み（同じ手元の D1）: 新しい行の INSERT は sessions 3→4、rec_stage 3→4、rec_card 2→3。既にある rec_stage への upsert も 2→3（tour が変わらなくても 1 増える。start の索引と同じ）。DELETE は手元ではどれも 1（本番の DELETE の数え方は未確認なので、見積もりは入れるのと同じだけ数える）。

1 日の増え方の見積もり: sessions はログイン 1 回に 1（300 人で数百）。rec_stage は差分で変わった行ごとに 1（Catalog #9 で 145 行、初回でも 4,818）。rec_card は毎日作り直すので「カードの数（約 1,557）× 入れる・消す」で約 3,100。deliver_catalogue.py の見積もり（rec_stage は 1 行 +2、カードは 1 行 3）と、題名・カードに残す分（15,000 → 18,000）を直した。

users(created_at) は足さなかった: 利用者は 300 人まで（rate-limit.js）なので、読むのは 1 回最大 300 行で頭打ち。

分からないこと: 本番の D1 が DELETE で索引の分も数えるか。本番のレイテンシ（#138）。作り物の tour の分け方（1 公演 1〜8 会場）が本番とどれだけ違うか（索引ありの読み取りは同じ tour の行数だけなので、大きくは変わらない）。
