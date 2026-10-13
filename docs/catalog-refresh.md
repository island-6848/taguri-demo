# 公演カタログの定期更新

公開サーバーが読む公演カタログ（S3 の `stage-catalog/data.tar.gz`）を、手元のサーバー（EC2）で定期的に作り直して載せ直す。

> **2026-10-13: EC2 は無い**〔no-ec2〕。この文書の「EC2」で動かす手順は、いまどこでも動いていない。置き場所は非公開リポジトリの GitHub Actions を勧めている〔dec-crawler-gha-private〕。カタログの古さは公開の `/api/health` の `catalog` と、毎日の `Catalog age` ワークフローで確かめられる〔catalog-age-check〕。

## 流れ

| いつ | 何をする | 取得の量 |
|---|---|---|
| 毎日（日曜を除く）4 時台 | 一覧・お気に入りの名前の検索・ステイジーズカレンダーを取り直す（`run.py --no-open`） | お気に入りの検索は 3 日間控えるので、多くの日は数十件 |
| 日曜 4 時台 | 候補・クレジット・あらすじまで取り直す（`run.py --no-open --fetch`）。取るのは新しい公演と前回取れなかった分だけ | 数百件 |
| 毎回の終わり | 公開してよいファイルだけをまとめ、検査し、前のものを `history/` に控えてから S3 に載せる | ─ |
| 公開サーバー | 6 時間ごとに S3 の ETag を見て、変わっていれば入れ替える（`CATALOG_REFRESH_HOURS`） | ─ |

取得はすべて [`tools/lib/polite_http.py`](../tools/lib/polite_http.py) を通る。名乗り・robots.txt・ホストごとの間隔・429/503 で引く、の作法は[取得の方針](crawler-policy.md)に書いた。

## 他の利用者のお気に入りも探す

お気に入りに登録した名前は、毎日の更新でその名前の「これからの公演」を CoRich に探しに行く。以前は持ち主の登録しか探しておらず、**他の利用者が登録した名前は、手元にある公演の中で照合されるだけだった。** 今は次の流れで、全利用者の登録名を探す。

1. 公開サーバーの `/api/catalog/favourite-names` が、全利用者の登録名を重複除去して返す。返すのは種類・名前・登録している人数だけで、利用者 ID は返さない。URL・メールアドレス・長すぎる名前は返さない。合言葉（`TAGURI_NAMES_TOKEN`）を設定していなければ、この道は存在しない（404）。
2. 手元の `favourites.py` がそれを読み、持ち主の登録と重複を除いて、**1 回に 300 件まで**探す（登録している人数の多い順。名前ごとの結果を 3 日間控えるので、控えの古い名前から順に回る）。公開サーバーが眠っていて読めないときは、持ち主の登録だけで続ける。
3. 見つかった公演はカタログの `favourites.jsonl` に入り、各利用者の画面では、その人の登録名で照合して「お気に入り」に出る。

この口は**サービス版のサーバーにだけある**（デモ版では常に 404。[デモ版とサービス版](editions.md)）。設定は、サービス版のサーバー（Render）の環境変数 `TAGURI_NAMES_TOKEN` と、手元の `/etc/taguri/catalog.env` の `TAGURI_NAMES_URL`・`TAGURI_NAMES_TOKEN` に同じ合言葉を入れるだけ。

## 探しても見つからない公演を、次の更新で探す

公開版は、訪問者の操作で外部サイトを検索しない。そのため、手元のカタログに無い公演は「探す」でも「手で足す」でも見つからなかった。今は次の流れで補う。

1. **頼む：** 「探す」で見つからなかったとき、または「手で足す」の検索で見つからなかったときに、「次の更新で探してもらう」ボタンが出る。押すと、公開サーバーがその題名を本人の依頼として控える（`/api/search_request`）。「観ればよかった」を登録したときは、押さなくても自動で控える。
   - 1 人が控えておける依頼は 30 件まで（古いものから消える）。URL・メールアドレス・1 文字や 61 文字以上の題名は受け付けない。
2. **まとめる：** 公開サーバーの `/api/catalog/search-requests` が、直近 30 日の依頼を題名ごとにまとめて返す（依頼した人数とどの画面からかだけ。利用者 ID は返さない）。合言葉はお気に入りの登録名と同じ `TAGURI_NAMES_TOKEN`。
3. **探す：** 毎日の更新で `fetch_requests.py` がそれを読み、CoRich で探す。1 回 60 件まで（依頼の多い順・控えの古い順）、同じ題名は 7 日間探し直さない（見つからなかった題名も控える）。
4. **届く：** 見つかった公演は `picked.jsonl` に入ってカタログに載り、翌日から「探す」と「手で足す」の候補に出る。

依頼を読む URL は `TAGURI_REQUESTS_URL` で指定できる。未設定なら `TAGURI_NAMES_URL` と同じサーバーの `/api/catalog/search-requests` を使う。

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
