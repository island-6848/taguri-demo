# 公演カタログの定期更新

公開サーバーが読む公演カタログ（S3 の `stage-catalog/data.tar.gz`）を、手元のサーバー（EC2）で定期的に作り直して載せ直す。

## 流れ

| いつ | 何をする | 取得の量 |
|---|---|---|
| 毎日（日曜を除く）4 時台 | 一覧・お気に入りの名前の検索・ステイジーズカレンダーを取り直す（`run.py --no-open`） | お気に入りの検索は 3 日間控えるので、多くの日は数十件 |
| 日曜 4 時台 | 候補・クレジット・あらすじまで取り直す（`run.py --no-open --fetch`）。取るのは新しい公演と前回取れなかった分だけ | 数百件 |
| 毎回の終わり | 公開してよいファイルだけをまとめ、検査し、前のものを `history/` に控えてから S3 に載せる | ─ |
| 公開サーバー | 6 時間ごとに S3 の ETag を見て、変わっていれば入れ替える（`CATALOG_REFRESH_HOURS`） | ─ |

取得はすべて [`tools/lib/polite_http.py`](../tools/lib/polite_http.py) を通る。名乗り・robots.txt・ホストごとの間隔・429/503 で引く、の作法は[取得の方針](crawler-policy.md)に書いた。

## 壊れたカタログを載せない

`publish_catalog.py` は、次のどれかなら S3 に載せずに止まる（終了コード 1）。

- これから観られる候補が 100 件未満
- 前回載せた件数の半分を下回った（確かめたうえで `--force` を付ければ載せる）
- 載せてはいけないファイル（認証・DB・購入の記録・持ち主の分析）や、リンク・危ないパスが混じった

前のカタログは `stage-catalog/history/` に新しい順に 8 個残る。戻すときは、そこから `data.tar.gz` へコピーする。

## はじめて設定するとき（EC2）

1. **S3 への書き込み権限。** `stage-catalog/` の下に `GetObject`・`PutObject`・`DeleteObject`・`ListBucket`（prefix 限定）を許すロールを EC2 に付ける。公開サーバーが使う読み取り専用の `taguri-catalog-reader` とは分ける。
2. **設定ファイル。** `tools/taguri/deploy/catalog.env.example` を `/etc/taguri/catalog.env` にコピーし、`GEMINI_API_KEY` と `OWNER_USER_ID` を入れる（`chmod 600`）。
3. **まず手で試す。**
   ```bash
   python3 tools/taguri/publish_catalog.py --no-update --dry-run --out /tmp/catalog.tar.gz
   python3 tools/taguri/publish_catalog.py --mode daily
   ```
4. **タイマーを入れる。** `tools/taguri/deploy/` の 3 ファイルを `/etc/systemd/system/` に置き、`WorkingDirectory` と `User` を環境に合わせてから:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now taguri-catalog@daily.timer taguri-catalog@weekly.timer
   systemctl list-timers 'taguri-catalog*'
   journalctl -u 'taguri-catalog@*' -n 50     # 結果とホストごとの要求数・手を引いたホスト
   ```

## 公開サーバー側の入れ替え

動いたまま入れ替えるのは、利用者の保存先がカタログと別の場所にあるとき（`TAGURI_STATE_DIR` を設定しているとき）だけである。未設定だと利用者の SQLite が `data/` の中にあり、`data/` ごと入れ替えると開いている DB を壊すため、その場合は次の再起動まで入れ替えない。Render の無料プランは使われないと止まり、次に開かれたときに起動し直すので、そのとき新しいカタログを読む。
