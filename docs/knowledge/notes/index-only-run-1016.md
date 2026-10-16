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

追記（Catalog #9、05:30 UTC、https://github.com/island-6848/taguri-crawler/actions/runs/38856122652）: 原作の国 韓国の印（impl-origin-korea-tag）を入れたあとの索引だけの実行。2,841 行（公演 145 件・消す 1）、1 ファイルで success。版 dd2c1195b3545d54、残り 38,586 行。見積もり 5,827 書き込みに対し D1 の rows_written は 2,998（約 0.51 倍）。索引の postings は 33,412 → 33,424（+12、印の付いた会場の分と見られる。SQL の中身はログに出ないので、'#原作の国' の行そのものは確かめていない）。控えは 77,302 / 80,000、今日の残り 2,698。今夜の定期実行（同じ UTC の日に配る）は公演一覧・題名・カード・過去の公演がほぼ入らない。UTC 0 時で戻る。

訂正（2026-10-16、d1-upsert-counts）: #7 は 7009 と出たが、import は D1 の側で終わっていた（#8・#9 の rows_written が「1 行 1」で、既にある行への upsert の数え方だった）。上の「D1 には入っていないはず」は誤り。#8・#9 の「見積もりの約 0.5 倍」は、見積もりの誤りではなく送り直しのため。
