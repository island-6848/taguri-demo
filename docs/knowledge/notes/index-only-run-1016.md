---
id: index-only-run-1016
type: finding
status: confirmed
date: 2026-10-16
title: 索引だけの実行で、推薦の索引の初回 1.2 万行（公演 3,510 件）が本番 D1 に入った。1 つのファイルで送ると D1 の import が 7009 で止まり、1 MB ずつに分けたら通った
sources:
  - https://github.com/island-6848/taguri-crawler/actions/runs/38851892982
  - https://github.com/island-6848/taguri-crawler/actions/runs/38853274508
  - cloudflare/scripts/deliver_catalogue.py
links:
  - answers: q-index-load-now
  - depends_on: dec-index-only-run
---
取得の実行のログ（一次情報）から。
- Catalog #7（04:41 UTC、mode index）: 索引 2 万行（公演 3,897 件）を作った。見積もり 43,897 書き込み。index-upload.sql 1 つを wrangler d1 execute --file で送ったら、60 秒後に "A request to the Cloudflare API (/d1/database/…/import) failed. Upstream service unavailable [code: 7009]"。commit はしていないので、ハッシュは前のまま（次回また送る）。wrangler は「失敗したら元に戻る」と出すので、D1 には入っていないはずだが、本番を直接は確かめていない（開発の箱から本番には接続できない）
- 直したこと: deliver_catalogue.py が索引を 1 MB ずつ（文の切れ目、index-upload-01.sql …）に分け、ワークフローが名前の順に 1 つずつ送る
- Catalog #8（04:57 UTC）: 12,034 行（公演 3,510 件、開幕の近い順）、4 つに分けて全部 success。版 b0974b41cedec738、残り 41,409 行。**D1 が返した rows_written は 2,672 + 2,750 + 1,420 + 8,706 = 15,548 で、見積もり 27,578 の約 0.56 倍**（見積もりは多めの側）
- 無料枠の控え（取得の分、UTC 10-16）は 71,475 / 80,000 で 8 割を越え、Free-tier check が赤くなった。中身は #7 の失敗分 43,897（書く前に足すので、書かれなかった分も入る）と #8 の見積もり 27,578。D1 の実際の書き込みはこれよりかなり少ないはずだが、控えは減らさない（少なく数えないため）
- 今日（UTC 10-16）の残りは 8,525。今夜の定期実行（22:18 UTC ごろ始まり、配るのは同じ UTC の日）は、公演一覧・題名・カード・過去の公演の分が足りず、一部が「予算越え」で止まりうる。UTC 0 時（日本時間 9 時）で控えは戻る

分からないこと: 本番の /api/screen/recommend の diag が埋まったか（ここからは本番に接続できない）。見積もりと実際の差（1 行 2.3 書き込みの見積もりに対し実際 1.3）が、rec_gram を含まないこの回だけのものか。
