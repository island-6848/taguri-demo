# Renderをやめる：元の画面をCloudflare Workerへ移す計画

2026-10-13 決定（起案者）:

- Renderの他人の記録は引き継がない（デモ扱い）。
- 持ち主（EC2）の記録もアカウントに入れない。メール取り込み・Gemini・ふりかえりの作り直しなど持ち主専用の機能はEC2に残す。
- 画面は**今の見た目のまま**移す。Pythonが組んでいる画面（`/api/screen/*` の `body_html`）を1枚ずつWorkerのJSに移し、**Pythonと同じHTMLが出ることをテストで確かめる。**

## いまの形

- 画面の外枠と操作のJS（`web/app.js` → `cloudflare/public/app.js`）は静的ファイル。中身は `GET /api/screen/<名前>` が返す `{ok,title,body_html}` で、RenderのPython（`tools/taguri/serve.py`・`app.py` ほか約2.5万行）が組んでいる。
- 書き込みは `POST /api/<操作>`（約30種類）。保存先はRenderのSQLite（`ratings.db`・`auth.db`）で、Render独自のセッション（`tg_session`）で利用者を分けている。
- Workerはこれらを `ORIGINAL_UI_BRIDGE` でRenderへ中継している。ログイン（Firebase・パスキー）とは別の利用者になっている。

## 移したあとの形

- `/api/screen/*` と `POST /api/*` をWorkerが自分で答える。保存先はD1、利用者はログインしたアカウント（`users.id`）。
- 公演カタログなど利用者によらないものは、非公開リポジトリ taguri-crawler の毎日の取得（GitHub Actions）で作ってD1に入れる（`cloudflare/scripts/deliver_catalogue.py`、〔dec-d1-catalogue-delivery〕）。EC2 は無い（〔no-ec2〕）。Workerは表示に要る行だけを読む。
- Workers無料枠（1回のCPU約10ms）に収めるため、重い計算は前もってバッチで済ませ、利用者ごとの結果は保存して使い回す（`rec_cache` と同じ）。

## 進め方

**（2026-10-14 に変更）本番はもう切り替えた。** 起案者の指摘「本番用のサイトなはずなのに、デモ用の内容がでる」で、`NATIVE_UI=all` にし、まだ移していない画面は「いま新しい仕組みに移しています」と出す（〔dec-native-cutover-now〕）。**同日、元の画面はすべて Worker に移し終えた**（最後は眺める〔dec-records-worker〕）。眺めるの人の流れ・相関図は CPU 10 ミリ秒を越えるので、Worker では組まずにブラウザで組む。以下は当初の方針: **本番は最後に一度だけ切り替える。** 移植途中の画面を本番に出すと、Worker側とRender側で記録が分かれて混乱する。移した画面は環境変数 `NATIVE_UI`（移した画面の名前の一覧）で手元とテストだけで有効にし、全部そろったら本番で有効にしてRenderへの中継を外す。

**一致の確かめ方。** Python側は既存の試験用サーバー（`tools/taguri/test_demo_stability.py` と同じ、一時DB・外部通信なし・service版）で、決めた手順（記録を足す・評価する・画面を開く…）を流し、各応答を書き出す。Worker側は同じ手順を同じ架空カタログで流し、`body_html` と応答が一致することを確かめる。日付は固定する。

| 段 | 内容 | 画面 | 操作 |
|---|---|---|---|
| 0 | 土台 | — | D1の表（works・hand_credits・merges・excluded・visit_note・reaction・ticket・missed・rank_weight・app_setting）、画面の振り分け、一致テストの仕組み |
| 1 | 記録と評価 | rate・unrated・notes・works（日記帳） | rate・note・add_work・fix_work・merge_work・drop/restore/purge_work・link_stage・hand_credits・visit_note |
| 2 | おすすめ | recommend・interest・favourites | react・favourite・decline・weight・pref_setting・recommendation/visit・contact |
| 3 | 予定 | reminder・calendar・tickets | ticket |
| 4 | 探す・ふりかえり・設定 | search・records・trace・chronicle・settings・start・register | missed・search_request |
| 5 | 切り替え | — | 本番で `NATIVE_UI` を全画面にし、中継（`original-ui.js`）を外す。D1の旧 `records` 表（「アカウント・記録」の画面）を works に移す。Renderを止める |

持ち主専用で移さないもの: import_mail・mail_hints・chronicle/people_read の作り直し（Gemini）・hand_theme・hand_poster・close・ふりかえり（lookback）・外部の公演検索（suggest_web の外部分）。Renderの公開版でもすでに止まっているもの。デモ版の96件の種まきも移さない（本番は空から始まる）。

## 確かめること（切り替え前）

| 項目 | 方法 |
|---|---|
| 全画面がPythonと同じHTMLを出す | 一致テスト（CI） |
| 無料枠のCPU時間に収まる | 実カタログ相当の量で各画面の計算時間を測る |
| D1の読み書き行数が無料枠（1日500万行読み・10万行書き）に収まる | 画面ごとの読み込み行数をテストで数える |
| 切り替え後にRenderへ1件も要求が飛ばない | 中継を外した状態のテストと、本番のログ |
| 利用者の記録がほかの利用者に見えない | 2人の利用者で同じ手順を流すテスト |
