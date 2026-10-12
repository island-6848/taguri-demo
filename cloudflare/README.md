# 元の画面を維持する移行途中版

現在の公開ルートは元の `web/` のHTML・CSS・JavaScript・動画・D3を再利用します。画面名と17画面のフラグメントAPI、既存の操作を維持するため、画面生成とその書き込みは一時的に既存Renderへ接続します。**Renderからの完全移行はまだ完了しておらず、この段階でRenderを停止してはいけません。** コールドスタートとSQLiteの再起動時の制約も引き続きあります。

元のCSS、チュートリアル、動画、D3は元リポジトリの同じファイルを配信します。JSの変更はAPIの同一オリジン化と配信パスのみです。元の認証Cookie `tg_session` とD1のCookie `taguri_session` を分離し、D1のCookieをRenderへ送信しません。HTMLフラグメントは変更せず、利用者の応答を共有キャッシュへ入れません。

簡易版で保存済みのD1記録と復旧コードは保持しています。持ち出し用の旧画面は `/migration-data/`、そのAPIは `/migration-api/` に隔離しました。元の画面とD1の記録はまだ自動統合していません。元のサーバーのJSON/ZIP出力は全利用者の記録を含む実装のため、この橋渡しでは公開せず、利用者単位の書き出しを移植してから提供します。

GitHub ActionsではPC(1280px)/スマホ(390px)で元の6画面と復元画面を比較します。同じ合成アカウントのPython生成HTMLを双方で使い、スクリーンショットの差分とJS例外を確認します。このテストは公開中の実データやRenderの可用性の確認とは別です。D1側の96件保存・復旧テストも残します。

---

# Cloudflareへの移行プレビュー

Renderを止める前に検証する独立した移行版です。現行のPython版、GitHub Pagesの公開手順は変更しません。

実装済み: 同一オリジンの静的画面・API、D1への観劇記録/評価/感想/お気に入り・公演への反応保存、復旧コード認証、利用者ごとのデータ分離、JSONの持ち出し/再取り込み。DBへの操作はインデックスと件数上限を使います。画面は保存後に必要な表示だけ更新し、再読み込みやPythonプロセスの起動を待ちません。

移植済みの照合: 現行の `declared_hits` に基づき、人/作品/団体/主催/題材/原作者を候補に照合。興味あり/興味なし/購入済みの保存と分類、上演中・終了済み公演の分離も行います。順位付きの統計推薦はまだ移植していません。

未移行: 現行の統計推薦・分析・カレンダー・公演検索・購入メール取り込み・端末追加コード・画像配信。お気に入り照合は候補データをD1へ取り込んでから利用できます。現行の全機能と同等ではありません。非公開の公演候補・クレジット・推薦計算用データは公開リポジトリに存在せず、移行前に取得と許諾範囲の確認が必要です。所有者の推薦順位/理由を一般利用者にコピーしてはいけません。

## 無料運用の方針

- Cloudflare Workers **Free** とD1から始め、`workers.dev` のURLを使用します。有料プラン・独自ドメイン・R2・Supabase・外部LLMは不要です。このコードから有料プランへ変更する処理はありません。
- 無料枠の最新の制限/課金条件はCloudflareダッシュボードで確認してください。無料枠超過時の停止を許容する構成です。通常運用が無期限に無料になることを保証するものではありません。
- プレビューは100アカウント、1人500記録/200お気に入り/500公演反応まで。これらは**保存量の上限**であり、攻撃やアクセス集中時のリクエスト数を抑えるものではありません。公開前にCloudflareで利用量とアクセス制御を確認します。新規登録は `ALLOW_REGISTRATION=false` で停止できます。
- private APIは `no-store`。復旧コード/セッションはSHA-256ハッシュのみD1に保存し、256bitのランダム値を使用します。セッションは30日、CookieはHttpOnly/Secure/SameSite=Strict。コードを保存しないと復旧できません。

## 公開前のセットアップ

Cloudflareの無料アカウントとブラウザでのログインが必要です。パスワード/APIトークンをチャットやGitHubに貼らないでください。

```sh
cd cloudflare
npm install
npx wrangler login
npx wrangler d1 create taguri-demo
```

作成結果の `database_id` を `wrangler.jsonc` の `REPLACE_WITH_CREATED_D1_ID` に置き換えます。ローカルDBとリモートDBは別です。

```sh
npx wrangler d1 migrations apply taguri-demo --local
npm test
python3 -m unittest discover -s test -p 'test_*.py'
npm run dev
# local preview verified, then create the remote tables and publish a separate preview:
npx wrangler d1 migrations apply taguri-demo --remote
npm run deploy
```

`npm test` は外部接続不要のSQLite統合テストです。Cloudflareランタイムの検証は `wrangler dev` と公開先で別途行います。Wranglerの依存関係は接続できる環境でインストールし、生成したロックファイルをコミットしてください。プレビューのHTMLに未移行機能を明記しています。

公開後、端末Aで登録→追加→評価→再読み込み、端末Bで別アカウントの分離と復旧コードの復旧、エクスポート/取り込みを確認します。初回に発行されるコードを控えてください。Workers/D1の使用量も確認します。

## 記録の移行

まず現行のDB・非公開データ・認証用pepperをバックアップします。現行の `export_payload()` は複数ユーザーを含む可能性があるため、公開APIの一括エクスポートを移行用に使わず、DBを読み取り専用で利用者IDごとに変換します。

```sh
python3 scripts/convert_records.py --database /secure/review.db --user-id USER_ID --output private-exports/records.json
# The selected purchase fixture already in the repository can also be converted:
python3 scripts/convert_records.py --purchases ../tools/taguri/demo_purchase_works.json --output private-exports/purchases.json
```

移行版で新規登録してコードを控え、該当利用者のJSONだけを「取り込む」で読み込みます。出力ファイルにはuser_id/復旧コード/購入メール本文を入れません。IDは安定しているため再取り込み時に同じ記録は増えません。DBの `app_setting` にある利用者別のお気に入りと `reaction` の三択反応も引き継ぎます。所有者のファイル形式のお気に入りは、その人専用の `declared.json` を `--declared` に明示してください。旧エクスポートのv1形式も新版で読めます。

変換対象は作品ごとの初回日・時刻・会場・評価・感想です。各回の評価、複数回観劇、動機、反応の理由、券、除外、統合設定、手動クレジット等はこのプレビューには引き継がれません。原本DBを保持し、これらの引き継ぎが実装されるまでは現行版を停止しません。ユーザーの旧Base32復旧コードはscrypt/pepper方式のため、新版の復旧コードへ自動的には引き継げません。

**切替の条件:** 公開先での保存・復旧検証、全利用者のバックアップ、推薦を含む必要機能の移植、実データ件数と評価の照合が完了してから案内URLを更新し、最後にRenderを停止します。このPRだけでRenderを停止しません。

## 候補データの取り込み

公開情報だけの候補JSONLを用意し、変換後に内容を確認します。候補は1000件まで。所有者の順位・推薦理由・感想・個人的な登録名はコピーしません。公開情報のクレジットとあらすじだけを照合用に持ちます。

```sh
python3 scripts/convert_catalogue.py --input /secure/candidates.jsonl --output catalogue.sql
npx wrangler d1 execute taguri-demo --remote --file catalogue.sql
```

APIの候補は公開情報だけで5分キャッシュ可能です。照合はブラウザ内で行い、LLMや外部APIへの従量課金はありません。記録・お気に入り・反応は利用者別のprivate APIで取得します。GitHub ActionsのプレビューチェックはテストとWranglerのdry-runのみ実行し、公開やDB変更をしません。

## 推薦をRenderから外す：段1（推薦の索引）

`tools/review/user_recommender.py`（person-feedback-v1）は、表示のたびに公演カタログ全体を読み直し、全公演の出演者・スタッフ欄を分解している。**利用者によらない部分をバッチで1回だけ作り、D1に入れる。** Workerは、本人が◎を付けた人の行だけを読んで点数を足す。

| 表（`migrations/0003.sql`） | 中身 |
|---|---|
| `rec_stage` | 候補の公演。公開項目・期間・分解済みのクレジット |
| `rec_credit` | （役職, 人物）→ 公演。役職の重みとまとめを付けてある |
| `rec_people` | 公演 → 人物。評価した記録から本人の表を作るため（過去の公演を含む） |
| `rec_meta` | いま使う版（`current`） |

作り方（カタログのある環境＝EC2で、`publish_catalog.py` の後に）:

```sh
python3 cloudflare/scripts/build_recommend_index.py --output /tmp/rec.sql --stats /tmp/rec-stats.json
npx wrangler d1 execute taguri-demo --remote --file /tmp/rec.sql
```

新しい版を入れてから `rec_meta.current` を切り替え、古い版を消す。途中で失敗しても前の版のまま動く。持ち主の得点・理由・感想・反応は索引に入れない。

**一致の確認。** `scripts/build_recommend_index.py` の `score_from_index` が、Workerが毎回行う計算の仕様（参照実装）である。`test/test_recommend_index.py` は、作った架空のカタログと評価で、これが現行の `user_recommender.prepare` と**同じ公演・順位・点数・理由・強さ**を出すことを、メモリ上の索引とSQLite上の索引（D1と同じ問い合わせ）の両方で確かめる。

**まだ確かめていないこと。** 実カタログでの件数とD1の読み込み行数（`--stats` の `postings_per_person` から見積もる）、WorkerのCPU時間。D1の `records` 表は公演IDを持たないため、評価した記録を `rec_people` に結び付ける列が段2で要る。手で入れた出演者（`hand_credits`）にもまだ対応していない。

## ログイン：Firebase Authentication（作業中）

会員登録はFirebase Authenticationに任せる。**パスワードは使わない**（Googleログインと、メールに届くリンクだけ）。Workerは、ブラウザから届いたFirebaseのIDトークンを `src/firebase-auth.js` でGoogleの公開鍵を使って確かめ、たぐりのセッションを新しく発行する。

- **D1に入れるのはFirebaseのUIDだけ。** メールアドレス・名前・写真は保存しない（`migrations/0004.sql`）。トークンを確かめる処理もUID以外を返さない。
- 確かめる項目：RS256の署名、鍵ID、`aud`（プロジェクトID）、`iss`、`sub`、期限、発行時刻、**ログインが5分以内であること**（古いトークンの使い回しを防ぐ）、ログイン方法がGoogleか確認済みメールであること。
- ログインのたびにセッションを作り直し、ログイン前のセッションは消す。`POST /api/logout/all` で全端末からログアウトできる。
- 復旧コードで使っている人がログインすると、そのアカウントにFirebaseを結び付け、記録を引き継ぐ。**既にある2つのアカウントは自動で合わせない。**
- Googleの公開鍵は最大6時間キャッシュする。知らない鍵IDでの取り直しは1分に1回まで。
- 今は `ORIGINAL_UI_BRIDGE` が `/api/*` をRenderへ渡すため、入口は `/migration-api/auth/firebase`。ログイン画面（ブラウザ側のFirebase SDK）はまだ作っていない。

**Firebaseの設定（持ち主が行う）**

1. Firebaseコンソールでプロジェクトを作る（無料のSparkプラン。カード登録は不要）。
2. Authentication → ログイン方法で **Google** と **メールリンク（パスワードなしでログイン）** を有効にし、**メール/パスワードのパスワードによるログインは無効**にする。
3. 承認済みドメインを、たぐりのWorkerのドメインだけにする。
4. 「メール列挙保護」を有効にする（登録済みかどうかを外から探られないようにする）。
5. プロジェクトIDを `wrangler.jsonc` の `FIREBASE_PROJECT_ID` に入れる（公開してよい値。秘密鍵やサービスアカウントの鍵は不要で、作ってもリポジトリやチャットに貼らない）。
6. `npx wrangler d1 migrations apply taguri-demo --remote` で `0003`・`0004` を本番のD1に入れる。
