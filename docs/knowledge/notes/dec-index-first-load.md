---
id: dec-index-first-load
type: decision
status: adopted
date: 2026-10-16
title: 推薦の索引の初回（約 5.3 万行）は 1 日の書き込みの予算に収まらないので、何日かに分けて入れる。公演ごとにまとめ、開幕の近い公演から
sources:
  - cloudflare/scripts/build_recommend_index.py
  - cloudflare/scripts/deliver_catalogue.py
  - cloudflare/test/test_recommend_index.py
  - cloudflare/test/test_deliver_catalogue.py
links:
  - depends_on: dec-index-diff
  - depends_on: d1-writes-undercounted
---
Catalog #6（run 38816233905、2026-10-15 22:18 UTC〜）の deliver_catalogue の報告（記録の取り込みのセッションが読んだ）: "index": "skipped: 111710 writes would exceed the budget"（差分の初回 53,446 行、rec_stage 4,818 行）、labels 9,616・cards 3,114 は入った、"d1_left_today": 44682。Free-tier の表は D1 の書き込み 57,088/80,000。このままでは毎日 skip され、索引が届かない。
- 直したこと: build_recommend_index.py --max-rows（diff_sql の limit）。変わる行が上限を越えるときは、消す行を先に、次に公演ごと（その公演の rec_stage・rec_credit・rec_people をまとめて）に開幕の近い順で、最後に題名の 2 文字の束（rec_gram）を、上限まで選ぶ。送らなかった行は前のハッシュのままなので、次回の差分にまた出る。途中の日は rec_meta 'index_rev' を「版-left残り行数」にして推薦の控えを捨てさせる
- deliver_catalogue.py: 上限は（予算 − それまでの書き込み − 題名とカードの分 15,000）÷ 3（1 行 2 ＋ rec_stage の索引の分を多めに）。全部入れ終えたときだけ版を控える（途中なら翌日も同じ版の残りを送る）。上限が 0 なら "skipped: no room in today's budget"
- 見込み: 予算 6 万から公演一覧とカードの分を引くと 1 日約 1.4 万行で、初回は 4 日ほど。途中の日も、開幕の近い公演から推薦に使える。過去の公演の投入（past_stage）は残りの予算で動くので、その数日は少なくなる
- 試験: 上限ずつ当てていくと、まるごと入れた表と同じになる。1 日目に入った公演は、その公演の出演・作り手の行がそろっている。開幕の近い公演が先

追記（2026-10-17、定期の確かめ）: Catalog #10（run 38973663053、schedule、2026-10-16 22:05 UTC 開始。予定の 19:17 から約 3 時間遅れ。GitHub の定期実行の遅れ）の deliver_catalogue の報告: `"index": "skipped: no room in today's budget (46736 rows left)"`、`"cards": "skipped: 6204 writes would exceed the budget"`、`"venue_census": "skipped: 2722 writes would exceed the budget"`、`"labels": "unchanged"`、公演一覧は 824 行が変わって送った（見積もり 2,478 → D1 が数えた 1,651。settle が控えを置き換えた）、`"d1_left_today": 220`。同じ UTC の日（10-16）に索引だけの手動実行で書いた分が控えに残っていたため、索引は 1 行も入らなかった（壊れたのではなく、上限の手前で止める仕組みが働いた）。
- 残り: 索引 46,736 行、カード 6,204 書き込み、劇場制覇マップの分母 2,722 書き込み
- 見込み: 新しい UTC の日の予算 6 万から、公演一覧（約 2,500）・分母（初日だけ 2,722）・題名とカードの取り置き 15,000 を引いて 3 で割ると 1 日約 1.3〜1.4 万行。46,736 行は 4 日（UTC 10-17〜10-20 の回。日本時間では 10/18〜10/21 の朝 7 時ごろの回）で入り終わる見込み。途中の日も開幕の近い公演から推薦に使える
- 実行が「失敗」と出たのは、最後の Free-tier check が D1 の書き込み 79,998/80,000（8 割越え）を **注意** として止めたため（設計どおり）。作業データ（state）の保存は済んでいる。過去の公演の名前の索引（R2）は 256 個すべて送った（101,224 名、49.5 MB）。R2 の Class A は今月 6,142 / 30 万、保存 0.34 GB / 8 GB

追記（2026-10-18 01:30 UTC、定期の確かめ）: Catalog #11（run 39070989750、schedule、2026-10-17 21:27 UTC 開始）は、Free-tier の plan が run:false を返して 45 秒で止まった（取得も索引も届いていない）。原因は Actions の見込みで先の週 1 の上乗せを必ず使う分に数えていたこと（別のセッションの報告。taguri-demo master f25038b で直した。crawler-run-1014 に記録）。直したあとの手動の実行 Catalog #12（run 39084288296、workflow_dispatch、00:51 UTC 開始）は、この時点でまだ動いている。索引の残り（46,736 行）の見込みは #12 の報告を見てから見直す（1 時間後にもう一度確かめる）

追記（2026-10-18 04:35 UTC、定期の確かめ）: Catalog #12（run 39084288296、workflow_dispatch、00:51〜04:10 UTC、**成功**）の報告（job のログから読んだ）。
- deliver_catalogue: `"index": "revision 4ebbe86d8b2a2e42 (14090 rows changed, 28554 writes, 31819 rows left for the next delivery)"`、`"cards": "version da2f1e82cbd8298c (6120 writes)"`（10/16 から止まっていたカードが入った）、`"venue_census": "1360 venues (1360 changed)"`、`"labels": "unchanged"`、公演一覧は変更 0、`"d1_left_today": 42598`。build_recommend_index の差分は upserted 10,236・deleted 3,854・公演 374。各段の rows_written: 2,725／655／18,455／588／4,618（D1 が数えた分）
- 過去の公演（past_stage）: 6,666 行・19,998 書き込みで送り、残り 1,469 行（ページの読み取りは 24,885 件、cursor 160,772 / 512,453）
- ポスター: 254 枚を R2 に入れたところで R2 への書き込みが HTTP 500 で止まった（"left": -1820 と残りの数え方もずれていた）。別のセッションが deliver_posters.py を直している（5xx は待ってやり直す）
- Free-tier の表（すべて ok、8 割越えなし）: Actions 直近 31 日 886 分 / 上限 1,500（無料 2,000）、D1 の書き込み（今日・取得の分）47,547 / 80,000（無料 10 万）、R2 の保存 0.37 GB / 8 GB、Class A 今月 6,653 / 30 万、Class B 1,822 / 300 万
- 見込みの見直し: 索引の残りは 31,819 行（前回 46,736 行）。この実行は UTC 10-18 の日の予算を使ったので、同じ UTC の日の定期実行（19:17 UTC 予定）では索引はほとんど入らない見込み。1 日約 1.4 万行として UTC 10-19・10-20 の回で約 2.8 万行、残り約 4 千行が 10-21 の回で入り終わる（日本時間では 10/22 の朝ごろ）。途中も開幕の近い公演から推薦に使える
