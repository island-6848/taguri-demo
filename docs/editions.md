# デモ版とサービス版

たぐりの公開版は、**デモ版**と**サービス版**の 2 つに分けて動かす。
画面のファイルは共通で、つなぐ API サーバーと保存先が別になる。

| | デモ版 | サービス版 |
|---|---|---|
| 画面の URL | `https://island-6848.github.io/taguri-demo/` | `https://island-6848.github.io/taguri-demo/app/` |
| API サーバー | Render のサービス `taguri-demo` | Render の別サービス（URL はリポジトリ変数 `TAGURI_SERVICE_API`） |
| `TAGURI_EDITION` | `demo`（未設定でもこれ） | `service` |
| 最初の記録 | 見本の架空の記録 96 件が入る | 何も入らない（本人が入れた記録だけ） |
| 記録の保存 | 一時保存でよい（消えると注記） | **永続ディスクの `TAGURI_STATE_DIR` が無いと起動しない** |
| 「探してほしい」題名 | 受け付けない | 受け付けて、毎日の更新で探す |
| 取得処理への口（`/api/catalog/*`） | **無い（常に 404）** | `TAGURI_NAMES_TOKEN` を設定すると開く |
| 画面の注記 | 「操作を試せるデモです」 | 出さない |

両方に共通するもの（公開運用としての守り）:

- Cookie と復旧コードで利用者を分ける。起動ごとの合言葉は使わない
- 共有の公演情報（あらすじ・題材・画像）は編集させない
- 訪問者の操作では外部サイトを検索しない（取得は毎日の更新だけ。docs/crawler-policy.md）
- 公演カタログは同じ S3 のもの（`stage-catalog/data.tar.gz`）を読むだけ

## なぜ分けたか

以前は `demo_mode` という 1 つのフラグが、意味の違う 3 つのことを兼ねていた。

1. 公開運用か（不特定多数が入る・復旧コード・編集の制限）
2. デモとしての振る舞い（見本の記録・「消えてよい」前提・デモの文言）
3. 1 つのサーバー・1 つの保存先を全員で使うこと

このままでは、本当に記録を残して使いたい人の記録が見本と同じ場所に入り、デモの訪問者の
操作（お気に入りの登録名・探してほしい題名）が本番の取得の量と向きを変えてしまう。
そこで 1 は `Server.public`、2 は `Server.edition` に分けた。3 はサーバーごと分けた。

## コードの上での切り分け

- `tools/taguri/serve_cloud.py` ── `TAGURI_EDITION` を読む。知らない値なら起動しない。
  サービス版で `TAGURI_STATE_DIR` が無ければ起動しない
- `tools/taguri/serve.py` ── `Server(public=..., edition=...)`。新規登録で見本を入れるのは
  デモ版だけ。`/api/catalog/*` はサービス版だけ。応答には `public`・`edition`・
  `demo_mode`（デモ版のときだけ真）を乗せる
- `tools/taguri/app.py` ── `EDITION` と `is_demo()`。見本の投入・結び付け、
  探してほしい題名の受け付け、検索結果の案内文、保存先の注記を版で分ける
- `web/config.js` ── 開いた URL（`/taguri-demo/` か `/taguri-demo/app/`）で版を決め、
  API の行き先を選ぶ。サービス版の API が未設定なら「準備中」を出す
- `.github/workflows/pages.yml` ── `TAGURI_SERVICE_API` を `config.js` に埋め、
  `app/index.html` を置く

検査は `tools/taguri/test_editions.py`（CI で実行）。

## サービス版を立てる手順

1. **Render に新しい Web サービスを作る**（デモの `taguri-demo` とは別）。
   起動コマンドはデモと同じ `python3 tools/taguri/serve_cloud.py`
2. **永続ディスクを付ける**（例: `/var/data` にマウント）
3. 環境変数を入れる:
   - `TAGURI_EDITION=service`
   - `TAGURI_STATE_DIR=/var/data/taguri`（永続ディスクの中。カタログの `data/` とは別）
   - `CORS_ORIGIN=https://island-6848.github.io`
   - `TAGURI_NAMES_TOKEN=<長い乱数>`（`python3 -c "import secrets; print(secrets.token_urlsafe(32))"`）
   - カタログの読み取り: `STAGE_CATALOG_BUCKET`・`STAGE_CATALOG_KEY`・`AWS_DEFAULT_REGION`・
     読み取り専用 IAM の鍵（デモと同じものでよい）
4. **GitHub のリポジトリ変数 `TAGURI_SERVICE_API`** に、そのサービスの URL
   （例 `https://taguri-service.onrender.com`）を入れ、Pages のワークフローを再実行する
5. **手元（EC2）の `/etc/taguri/catalog.env`** の `TAGURI_NAMES_URL` を、
   サービス版の `/api/catalog/favourite-names` に向ける。`TAGURI_NAMES_TOKEN` は 3 と同じ値
6. 確かめる: `/api/health` が `"edition": "service"` を返す。`/taguri-demo/app/` で
   見本の記録が入っていない。再デプロイしても記録が残っている

デモ版の Render サービスは `TAGURI_EDITION` を設定しないか `demo` にする。
`TAGURI_NAMES_TOKEN` はデモ版には要らない（入れても口は開かない）。

## 既存のデモの記録

デモ版で作った記録は、サービス版へ移さない。見本と本人の入力が混ざっていて、
どれが本人の記録か分けられないからである。サービス版は空の状態から始める。
