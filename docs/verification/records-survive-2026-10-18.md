# 再配備・カタログ更新・DB 移行のあとも本人の記録が残るか（2026-10-18、issue #137）

対象: master `2cc2125` に、このブランチの変更を足したもの。環境: ローカル（Node 22.22.0 の `node:sqlite`、Python 3.13 の `sqlite3`）。
本番・隔離環境の D1 では、まだ試していない（下の「まだ確かめていないこと」）。〔records-survive-1018〕

## 何を自動の試験にしたか

| 場面 | 試験 | 確かめること |
|---|---|---|
| DB 移行（配備のたびに `wrangler d1 migrations apply`） | `cloudflare/test/migrations-keep-records.test.js` | 0001〜N を当てた DB に、利用者の表（`users` と、`user_id` の列があるすべての表）へ 2 人分の行を入れ、残りの migration を当てる。N は 1 から最後の 1 つ前まで全部（今は 33 通り）。前からある列の値・行の数がそのまま、新しい列は宣言した既定値か決めた埋め方（`works.rated_at`）、外部キーが壊れていない。行のある DB で migration が失敗しないこと |
| 取得の毎日の配送 | `cloudflare/test/test_delivery_keeps_records.py` | 本物の配送のコード（一覧・推薦の索引の全部と差分・カード・公演の見出し・過去の公演・ポスター）が作った SQL を、利用者の行のある DB に流す。利用者の表が 1 行も変わらない。SQLite の authorizer で、書いた表が配送の表だけで、表の形を変えないこと。スクリプトのソースにも、利用者の表へ書く文が無いこと |
| 定期実行の片付け（`src/cleanup.js`） | `cloudflare/test/cleanup.test.js` | 記録の表のどれか 1 つに 1 行あれば消さない（表ごとに確かめる）。境の時刻（ちょうど 1 か月）。ログインの期限が 1 か月を越えない。選んでから消すまでに記録を足した人を消さない。消すのはその人の行だけ。`user_id` のある表は、記録に数えるか数えない理由を書くかのどちらか |
| 再配備（新しいコード・推薦の `VERSION`）と索引の入れ替え | `cloudflare/test/redeploy-keeps-records.test.js` | Worker のコードに `CREATE`・`ALTER`・`DROP` が無い。前の版の作り置き（`rec_cache`）は読まれず今の版で作り直し、記録の表は 1 行も変わらない。古い Cookie のまま主な画面が開ける |

新しい migration を足すと、試験は自動でその migration の前後も比べる。前からある値を書き換える migration（`UPDATE`・`DELETE` など）は、試験の `REWRITES`・`BACKFILLS`・`KNOWN_WRITING` に「どう変わるのが正しいか」を書かないと落ちる。

## 分かったこと

- 0001〜0034 の migration は、前からある利用者の値を変えない。例外は意図した 2 つだけ: 0025（2026-10-15 23:39 より前の興味ありの `reaction.source` を付け直す）と 0034（評価のある記録の `works.rated_at` を `updated_at` から始める。評価が NULL・空の記録は NULL のまま）。0033 の `users.tokens_valid_after` は NULL で始まる
- 配送が書く表は `catalogue`・`venue_pref`・`venue_census`・`rec_meta`・`rec_stage`・`rec_credit`・`rec_people`・`rec_gram`・`rec_card`・`stage_label`・`past_stage`・`poster` だけ。利用者の記録の `stage_id` は、公演が一覧・索引から消えても変わらない（外部キーで結んでいない）
- Worker のコードは DB の形を変えない。再配備で変わるのは推薦の作り置きの印（stamp の先頭の `VERSION`）だけで、古い作り置きは次に開いたときに上書きされる
- 片付けは、設定・パスキー・作り置きだけのアカウントを消す。これは privacy.html の 6（「設定だけを変えたアカウントも含みます」）のとおりで、不具合ではない。`rank_weight`（推薦の効かせ方）も設定として数えない

## 見つけて直したこと

- 片付けは、消す人を選ぶ文と、消す文（1 人 1 つの batch）が別だった。選んだ直後にその人がログインして記録を足すと、その記録ごと消えるおそれがあった（起きる時間はごく短い）。消す文ごとに同じ条件を確かめ直すようにした（`deleteAccountStatements` の `guard`）。D1 の batch は 1 つのトランザクションなので、条件が成り立てば全部、成り立たなければ何も消さない〔dec-sweep-recheck〕。書き込み・読み出しの増え方は、主キーの索引で引く確かめが 1 人 1 文あたり十数回で、1 日 50 人までなので無料枠に響かない

## まだ確かめていないこと

- 本番・隔離環境の D1 で、同じ手順（再配備・差分配送・migration）を実際に流すこと。ローカルの SQLite と D1 の違い（外部キーの扱い、migration の失敗時の巻き戻し）は、公式の文書を開けず確かめていない〔q-d1-migration-failure〕
- 途中で失敗した migration・配送の再実行と、コードの巻き戻し（古い Worker が新しい列のある DB を読む）
- 古い・新しいブラウザーでの再ログイン（試験は同じ Cookie で画面を開くところまで）
- `venue_pref`・`venue_census` を書く配送は、文面の検査だけで、流しては確かめていない（試験の一覧に劇場の都道府県のデータを入れていない）
- 手元の管理画面（`tools/admin`）が本番の D1 に書く文（公演の上書き・修正依頼の対応）は、この試験の外
