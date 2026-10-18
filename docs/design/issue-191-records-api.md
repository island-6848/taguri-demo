# 記録の公開 API と画面の保存先をそろえる（issue #191 の設計案）

確認日: 2026-10-18。対象: ブランチ fix-g4（master `0217394` から）。**実装はしていない。** 本番の D1 の行数は見ていない（開発の箱から本番に接続できない）。

## 結論

**画面の表（`works`・`reaction`）を記録の正本にする。** 公開 API（`/api/record`・`/api/state`・`/api/export`・`/api/reaction`・`/api/import`）は画面と同じ関数を呼ぶ薄い変換に作り直し、`records`・`reactions` は一度だけ `works`・`reaction` に移してから読み取り専用にし、最後に消す。両方の表に書く（二重書き）はしない。

## いま何が分かれているか

| 経路 | 書く表 | 読む表 | 場所 |
|---|---|---|---|
| 公開 API `POST /api/record`・`/api/record/delete` | `records` | — | `cloudflare/src/worker.js:598-607`（upsert は `:328-330`） |
| 公開 API `POST /api/reaction` | `reactions`（`status` が interest/no/owned の 1 行） | — | `worker.js:618-622`、`:80-81` |
| 公開 API `POST /api/import` | `records`・`favourites`・`reactions` | `records` ほか | `worker.js:624-634` |
| 公開 API `GET /api/state`・`/api/export` | — | `records`・`favourites`・`reactions` | `worker.js:331-334`、`:587` |
| 初回の質問 `GET /api/onboarding` | — | **`records`**（答えた公演を外す） | `worker.js:322` |
| 画面「記録を足す」`POST /api/add_work` | `works` | — | `screens/rate.js:404-445` |
| 画面の評価・感想 `/api/rate`・`/api/note` | `works` | — | `screens/rate.js:343-353`、`:371-401` |
| 画面の興味あり・持っている | `reaction`（日ごとの行、`label` = その日） | — | `screens/recommend.js:695-700`、`:743` |
| 日記帳・評価一覧など | — | `works`（`loadWorks`） | `screens/works.js:70` |
| 画面の書き出し `GET /export.json` | — | `works`・`reaction`・`ticket`・`excluded`・`missed` | `worker.js:415-420`、`screens/settings.js:77-88` |
| 推薦 `GET /api/recommend` | — | `works`・`reaction`・`favourites`（#119 でそろえ済み） | `worker.js:243-253`、`cloudflare/README.md:198` |

`favourites` はすでに 1 つ（公開 API の `worker.js:608-616` と画面の `screens/lists.js:808` が同じ表に書く）。
分かれているのは「観た記録」（`records` ↔ `works`）と「公演への答え」（`reactions` ↔ `reaction`）の 2 組。
公開 API を使っているのは今は `/migration-data/`（`public/migration-data/app.js:7-68`、`/migration-api/` 経由。`worker.js:529-533`）だけで、メニューからのリンクは外してある（`worker.js:404`、`:535`）。

ほかの食い違い:
- `/api/onboarding` は `records` で「答えた公演」を外すので、画面で記録した公演を初回の質問にもう一度出す（`worker.js:322`）
- `records`・`reactions` には 0035 の印のトリガー（`users.rec_rev`、`migrations/0035.sql`）が無く、`rec_cache` を手で消している（`worker.js:596-597`）
- 詳細（aspects）の書き方が違う: `records` は `story`・`+story`（`recommend.js:81` の `cleanAspects`）、`works` は 5 段階の印（`screens/rate.js:355-368`）

## 選択肢

| 案 | 中身 | 採否 |
|---|---|---|
| A. `works`・`reaction` を正本 | 公開 API を画面の関数（記録を足す・評価・感想・答え）を呼ぶ変換にする。旧表は移して止める | **採る** |
| B. `records`・`reactions` を正本 | 画面を旧表に寄せる | 捨てる。画面は回数・まとめ（`merges`）・外した記録（`excluded`）・手で直した出演者（`hand_credits`）・券（`ticket`）を `work_key` で持つ。`records` の列ではこれを表せず、画面 13 枚を書き直すことになる |
| C. 両方に書く | API と画面がそれぞれ両方の表に書く | 捨てる。issue が禁じている。片方だけ失敗した行、`id` と `work_key` の対応、消すときの往復で新しい食い違いを作り、書き込みも 2 倍 |
| D. 公開 API を止めるだけ | `/api/record` などを 410 にし、`/export.json` に案内する | A の最後の段として使う。今すぐやると `/migration-data/` で記録している人の手段が無くなる |

## A の形

1. **共通の関数を切り出す。** `screens/rate.js` の記録を足す（`addWorkAction` の `work_key` の決め方・結び付け直し・`autoLink`）、評価・感想（`saveWorkField`）、`screens/recommend.js` の答え（`reactRow`）を、`ctx` と検証済みの値を受け取る関数にする（画面の action はそれを呼ぶだけ）。新しい規則は作らず、いまの画面の動きをそのまま使う
2. **公開 API を変換にする**（`worker.js:596-634`）
   - `POST /api/record` → 記録を足す＋評価・感想・詳細。応答の `record.id` は `work_key`。既存の `id`（`legacy-…`・UUID）は移すときの対応表（下）で `work_key` に引き直す
   - `rating`（◎○△×・`4/5`）→ `works.verdict`（そのまま。`gradeOf` は同じ）。`note` → `note_impression`。`aspects` は `story`→気になった・`+story`→良かった の印に変換する
   - `POST /api/reaction` → `interest`→`{interest:1, owned:0}`、`no`→`{interest:0, owned:0}`、`owned`→`{owned:1}`（`screens/recommend.js:692` の `REACT` と同じ）、`source='api'`。`remove` はその公演の `reaction` の行を消す
   - `GET /api/state`・`/api/export` → `loadWorks`（`screens/works.js:70`）と `reactionsOf`（`screens/lists.js:79`）から、いまの `version:2` の形に詰め直す。中身を全部欲しい人には `/export.json` を案内する
   - `/api/onboarding` の「答えた公演」は `works.stage_id` で見る
3. **契約の試験**（issue の完了条件）: 同じ利用者で「公開 API で足す → `loadWorks` に出る → `/export.json` に出る」と「画面で足す → `/api/state` に出る」、評価・答え・消す でも同じことを確かめる

## 移し方と互換の段

| 段 | すること | 戻せるか |
|---|---|---|
| 0 | 本番で `SELECT count(*) FROM records` / `reactions` と利用者の数を数える（`wrangler d1 execute --command`。読みだけ） | — |
| 1 | 共通の関数と、公開 API の変換を入れる。旧表へは書かなくなる。`/api/state` は「`works` の記録 ＋ まだ移していない `records`」を返す（移し終えるまで、旧い記録が見えなくならないように） | 配備を戻せば戻る（旧表はそのまま） |
| 2 | 移す: 利用者ごとに `records` → `works`（`work_key` は画面と同じ決め方、同じ鍵が既にあれば上書きせず飛ばして数える）、`reactions` → `reaction`（`label` は移した日）。移した `id` → `work_key` を `app_setting`（`key='legacy_ids'`）に残し、古い `id` で来た `/api/record` を同じ記録に当てる。移した人の `records` は消さずに残す | 消していないので戻せる |
| 3 | `/migration-data/` の記録の欄を外し、日記帳への案内にする（画面の変更なので、起案者に見せてから） | 戻せる |
| 4 | 30 日たって `/migration-api/record` 等の呼び出しが無ければ、旧 API を 410 にする | 戻せる |
| 5 | 控え（`backup_d1.py`）を取ってから `records`・`reactions` を消す migration。`cleanup.js:14-17` と `ACCOUNT_TABLES` からも外す | 控えから戻す |

## 無料枠

- 移すのは 1 回だけ。上限は 300 人 × 500 件（`records`）＋ 500 件（`reactions`）。1 行の書き込みは「行＋主キー＋ `rec_rev` のトリガーで `users` の 1 行」で約 3（`migrations/0035.sql:5` の数え方）。最悪 30 万行のときは 1 日の書き込み 10 万行を越えるので、**1 日に移す人数を `free_tier.py` の残りで決め、何日かに分ける**。実際の行数（段 0）が小さければ 1 日で終わる
- 段 2 の後、公開 API の書き込みは画面と同じ量。二重書きをしないので増えない。`/api/state` は `loadWorks` を使うぶん、`excluded`・`merges`・`hand_credits` を読む行が増える（1 回数百行まで）
- 保存の量は、移した後に旧表を消せば減る

## 危うい点

- `work_key` は題名と日付から作る（`screens/rate.js:425-434`）。同じ題名・同じ日の記録を API で 2 件持っている人は 1 件にまとまる。移す前に数え、まとまる組は `#時刻` 付きの鍵にする（画面と同じ規則）
- 応答の `id` が変わる（UUID → `work_key`）。外の利用者がいれば壊れるので、段 2 の対応表で古い `id` を受け付け続ける
- `reaction` は日ごとの行なので、`reactions` の「最後の状態だけ」とは数え方が違う。移した行は 1 日分の行として入れる
- `/api/import` の 1 回 40 項目・合計 500 件の上限（`worker.js:625-631`）と、画面の `works` の 2,000 件の上限（`migrations/0010.sql:79-82`）が違う。公開 API 側は 500 件のままにする

## やらないこと

- 公開 API の新しい版（`/api/v3` など）や、#161 の API 契約の全体はここでは決めない。この案は「同じ利用者の同じ記録が、どの経路でも同じに見える」までに絞る
