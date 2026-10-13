# デモ版とサービス版

たぐりの公開版は、**デモ版**と**サービス版**の 2 つに分けて動かす。
画面のファイルは共通で、つなぐ API サーバーと保存先が別になる。

| | デモ版 | サービス版 |
|---|---|---|
| 画面の URL | `https://island-6848.github.io/taguri-demo/` | Cloudflare Worker（今は workers.dev。独自ドメインは未定〔q-domain〕） |
| API サーバー | Render の無料プランのサービス `taguri-demo`。Render を止めたあとの扱いは未定〔q-demo-after-render〕 | Cloudflare Worker＋D1〔dec-workers-d1〕 |
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

**2026-10-13、サービス版は Cloudflare Workers＋D1 で動かすと決めた**〔dec-workers-d1〕〔dec-render-full-migration〕。
その前に書いた「Render の有料サービス」案と「VM＋Cloudflare の前段」案は置き換えた〔dec-render-service-beta〕〔dec-vm-cloudflare〕。
立て方・段取り・検証項目は [サービス化の進め方](service-roadmap.md) と、ブランチ `cloudflare-d1-preview` の `cloudflare/README.md` にある。

この文書の `TAGURI_EDITION=service` は、Render（`serve_cloud.py`）の上でサービス版を動かすときの切り分けとして残っている。
Worker 版でも、新しい利用者に見本を入れない・デモの入力を本番の取得に使わない、という切り分けは引き継ぐ。

## 既存のデモの記録

デモ版で作った記録は、サービス版へ移さない。見本と本人の入力が混ざっていて、
どれが本人の記録か分けられないからである。サービス版は空の状態から始める。
