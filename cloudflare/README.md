# 元の画面を維持する移行途中版

現在の公開ルートは元の `web/` のHTML・CSS・JavaScript・動画・D3を再利用します。画面名と17画面のフラグメントAPI、既存の操作を維持するため、画面生成とその書き込みは一時的に既存Renderへ接続します。**Renderからの完全移行はまだ完了しておらず、この段階でRenderを停止してはいけません。** コールドスタートとSQLiteの再起動時の制約も引き続きあります。

元のCSS、チュートリアル、動画、D3は元リポジトリの同じファイルを配信します。**`public/` の画面ファイルは `web/` の写し**で、masterで `web/` が変わったら、masterを取り込んだあとに `python3 cloudflare/scripts/sync_public_ui.py` で作り直します（古いままだと `test/test_sync_public_ui.py` がCIで落ちます）。JSの変更はAPIの同一オリジン化と配信パスのみです。元の認証Cookie `tg_session` とD1のCookie `taguri_session` を分離し、D1のCookieをRenderへ送信しません。HTMLフラグメントは変更せず、利用者の応答を共有キャッシュへ入れません。

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
| `rec_gram` | 題名の2文字の断片 → 公演（`migrations/0009.sql`）。記録を公演に結び付けるときの題名検索用 |
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
- `/api/auth/*` はRenderへの橋渡し（`ORIGINAL_UI_BRIDGE`）から外し、常にこのWorkerが答える。
- **ログイン画面は `/login`**（`public/login.html`）。Firebase SDK（`firebase@13.0.0`）は `src/client/login.js` から `npm run build:login` で `public/vendor/firebase-login.js` に組み立てて同梱する（外部のスクリプト配信元を使わない）。SDKを更新したら組み立て直してコミットする。
- `/login` だけはWorkerが専用のContent-Security-Policyを付ける。許すのは `apis.google.com` のスクリプト（ポップアップでのログインに要る）と、Googleのログイン用API、プロジェクトの認証ドメインの枠だけ。reCAPTCHA（電話番号ログイン用）は許さない。他の画面は `public/_headers` の方針のまま。
- FirebaseのログインはSDKのメモリ上だけに持ち（`inMemoryPersistence`）、Workerのセッションに切り替えたらすぐFirebase側はログアウトする。ブラウザの保存領域にFirebaseのトークンを残さない。
- ログイン後は `/migration-data/`（D1の記録の画面）に移る。**元の画面（Renderから橋渡ししている画面）はまだD1の記録を使わない**ので、ログインしても元の画面の中身は変わらない。

**Firebaseの設定（持ち主が行う）**

1. Firebaseコンソールでプロジェクトを作る（無料のSparkプラン。カード登録は不要）。
2. Authentication → ログイン方法で **Google** と **メールリンク（パスワードなしでログイン）** を有効にし、**メール/パスワードのパスワードによるログインは無効**にする。
3. 承認済みドメインを、たぐりのWorkerのドメインだけにする。
4. 「メール列挙保護」を有効にする（登録済みかどうかを外から探られないようにする）。
5. プロジェクトIDを `wrangler.jsonc` の `FIREBASE_PROJECT_ID` に、ウェブアプリの `apiKey` を `FIREBASE_API_KEY` に入れる。どちらも公開してよい値（`apiKey` はブラウザに渡す前提の識別子で、使える範囲は承認済みドメインとログイン方法の設定で絞る）。秘密鍵やサービスアカウントの鍵は不要で、作ってもリポジトリやチャットに貼らない。認証ドメインが既定（`<プロジェクトID>.firebaseapp.com`）でなければ `FIREBASE_AUTH_DOMAIN` も入れる。
6. 本番のD1への移行（`migrations/`）は、Workers BuildsのDeploy command（`npx wrangler d1 migrations apply taguri-demo --remote && npx wrangler deploy`）がデプロイのたびに適用する。手で入れる必要はない。

## ログイン：パスキー（Googleを使わない人向け）

指紋・顔認証・端末のロック解除で使えるパスキー（WebAuthn）。メールアドレスもGoogleもいらない。検証は `@simplewebauthn/server`（14.0.3）に任せ、`src/passkey.js` は誰が登録・ログインしてよいかと記録だけを受け持つ。

- `/login` の「パスキーで新しく始める」で、パスキーだけのアカウントを作れる。端末をなくしたときの備えに、**復旧コードを1回だけ表示**する（保存するのはハッシュだけ）。
- Google・メールリンク・復旧コードでログイン中なら、記録の画面（`/migration-data/`）の「パスキー」から追加できる。一覧と削除もそこにある（端末をなくしたとき用）。
- 本人確認（生体認証・端末のPIN）を必須にする。チャレンジは5分で失効し、1回使うと消える。未使用のチャレンジは全体で1000件まで。署名カウンタが進まない応答（複製された鍵）は拒否する。
- D1（`migrations/0005.sql`）に入るのは、公開鍵・クレジェンシャルID・ユーザーハンドル・カウンタだけ。1アカウント10個まで。
- RP ID はアクセスされたホスト名（`WEBAUTHN_RP_ID` で固定できる）。**ドメインを変えると、それまでのパスキーは使えなくなる**（復旧コードやGoogleでログインして、新しいドメインで追加し直す）。
- `test/passkey.test.js` はソフトウェアの認証器で、登録・ログイン・偽造（別のオリジン・別のRP ID・本人確認なし・別の鍵・ユーザーハンドルの不一致）・チャレンジの再利用と期限切れ・複製検知・他人の追加の横取り・削除を確かめる。手元の `wrangler dev` とChromeの仮想認証器でも、新規作成→ログアウト→パスキーでログイン、復旧コードのアカウントへの追加を通した。

## アカウントの削除（セキュリティ規約R7）

記録の画面の「アカウントを削除する」から `/login?purpose=delete` を開き、いつもの方法でログインし直してから「削除」と入力する。

- `POST /migration-api/account/delete`（`ORIGINAL_UI_BRIDGE` が有効な間、`/api/*` はRenderへ渡るため、D1のAPIは `/migration-api/` から呼ぶ）。
- **ログインし直してから10分以内のセッションでしか削除できない**（`sessions.created_at`、`migrations/0006.sql`）。長く使っているCookieを盗まれただけでは消せない。
- 記録・お気に入り・反応・パスキー・チャレンジ・全端末のセッション・アカウントを、表ごとに明示して消す（外部キーの連鎖に頼らない）。
- GoogleかメールのリンクでFirebaseと結び付いたアカウントは、Googleかメールでログインし直したときだけ削除できる。ブラウザがその場でFirebaseの利用者も消し、Google側にメールアドレスを残さない。
- Cloudflareの自動バックアップ（D1のTime Travel）には最大30日残る（画面にもそう書いた）。
- `test/account-delete.test.js`：全表から消えること、他人のデータは残ること、他の端末と復旧コードが使えなくなること、古いセッション・確認の誤り・別のオリジンの拒否、Firebaseと結び付いたアカウントの扱い、Renderへの橋渡しが有効でも届くこと。`wrangler dev` とブラウザでも、パスキーと復旧コードのアカウントで削除まで通した。

## ログインしていない人に見せるもの

ログインしていない人が開けるのは、**`/login`（ログイン）と `/about`（たぐりとは）だけ**。どちらもアプリのメニューを出さない、ロゴと中央のカードだけの画面（`public/auth.css`）。

- トップ（`/`）は `/about` へ、それ以外の画面は `/login?next=<元のパス>` へ転送する（`src/worker.js` の `gate`）。ログインすると `next` に戻る。`next` は同じサイトのパスだけを受け付ける（`//host`・`/\host`・外部URLは `/` に置き換える）。
- 元の画面の材料（Renderへの橋渡し：`/api/screen/*`・`/api/react` など）とポスター（`/img/*`）は、ログインしていなければ401。
- ログイン前でも使えるのは、ログインそのもの（`/api/auth/*`）、セッションを始めるAPI（`/api/register`・`/api/recover`、`/migration-api/*` は各APIが自分でログインを確かめる）、公開の公演一覧（`/api/catalogue`）、静的ファイル。
- 判定のため、`wrangler.jsonc` の `run_worker_first` を `/*` にし、CSS・JS・`/vendor/*`・`/assets/*` だけを外した（Workerの呼び出し回数を増やしすぎないため）。
- ログイン後の元の画面には、左のメニューに「アカウント・記録」（`/migration-data/`）を差し込む。`web/`（GitHub Pagesのデモと共通）は変えず、WorkerがHTMLRewriterで足す。
- `test/gate.test.js` と、`wrangler dev` とブラウザで確認した（未ログインでトップ→たぐりとは、他の画面→ログイン、ログイン後に元の画面へ戻る、メニューの入口、CSPの遮断なし）。

## 推薦をRenderから外す：段2（Workerでの計算）

段1の索引（`rec_*`）と本人の評価から、Workerが人物得点の推薦を計算する（`src/recommend.js`、`GET /migration-api/recommend`）。「アカウント・記録」の画面に「あなたへのおすすめ（試験版）」として出す。

- **Pythonと同じ結果。** `test/recommend.test.js` は、Python（`test/parity_fixture.py` が `score_from_index` で出した答え。段1でこれが `user_recommender.prepare` と一致することを確かめている）と、架空カタログ12×履歴4×重み3の144通りで、公演・順位・点数・理由・強さが完全に一致することを確かめる。計算をわざと壊すと落ちることも確認した。合わせるために、足し算と掛け算の順番、6桁の丸め（`toFixed` と同じ値になる速い丸め。約95万通りで一致を確認）、文字列のコードポイント順をPythonに揃えている。
- **記録と公演の結び付け。** `records.stage_id`（`migrations/0007.sql`）。結び付いた記録の人物が得点に効く。結び付いていない記録も、全体の◎率には数える（Pythonと同じ）。結び付けは下の「記録を公演に結び付ける」。
- **反応した公演（興味あり・興味なし・持っている）は外す**（Pythonの画面が別の一覧に移すのに合わせた）。ツアーの1枠化と、感想からの好み（impression preferences）はまだ移していない。重みの調整（つまみ）も無く、すべて既定の1.0。
- **結果の保存。** 利用者ごとに `rec_cache`（`migrations/0008.sql`）へ保存し、索引の版・日付（日本時間）・記録・反応が変わったときだけ計算し直す。記録・反応・取り込みを書き換えたら必ず消す。アカウント削除の対象にも入れた。
- **点数が付かない人は問い合わせない。** 寄与は「その人の◎率−全体の◎率」に正の重みを掛けたものなので、差が0以下の人はD1から読まない（結果は変わらない）。

**CPU時間と読み込み行数（この環境での見積もり。実データでは未測定）**

| 想定 | 読む行 | 計算時間（中央値） |
|---|---|---|
| 公演1,200・評価100（実データに近い想定） | 約5,400 | 約10〜12ms |
| 公演3,000・評価200・よく出る人に偏る（重い想定） | 約30,000 | 約39ms |

Workers無料枠のCPU時間（1回約10ms）には、重い想定では収まらない。計算し直すのは記録や索引が変わったときだけなので回数は少ないが、**実カタログで `build_recommend_index.py --stats` の数字を見て判断する**必要がある。収まらなければ、(1) 公演の開始日を `rec_credit` に持たせ、始まった公演をSQLの段階で除く、(2) Workers Paid（月5ドル、CPU時間30秒）に移る、のどちらか。

## 記録を公演に結び付ける

「アカウント・記録」の観劇記録に「公演を探して結び付ける」を付けた（`public/migration-data/link.js`）。記録の題名で探し始め、打ち直すと探し直す。**観劇日に上演していた公演を先に並べ**、次に題名が同じもの、題名で始まるもの、短い題名の順。選ぶと `records.stage_id` に入り、おすすめを計算し直す。

- **API。** `GET /migration-api/stages?q=題名&date=観劇日`（最大20件）と、`?ids=a,b,…`（結び付いた公演の名前。最大100件）。ログインが要る。返すのは索引の公開項目（題名・団体・劇場・都道府県・期間・公演ページのURL）だけ。
- **探し方。** 索引を作るときに題名を `rate_performances.title_key`（冠・記号・空白を落とす）で正規化し、2文字ずつの断片 → 公演 の表（`rec_gram`）を作る。題名を含む公演は必ず検索語の断片をすべて含むので、いちばん少ない断片の公演だけを調べればよい。1回の検索で読むのは断片の数の行（数行〜数十行）で、公演数によらない。2文字未満では探さない（Pythonの `app.suggest` と同じ）。
- **Pythonと同じ結果。** `search_index`（`scripts/build_recommend_index.py`）が仕様。`test/stage-search.test.js` は、Workerの検索がこれと全カタログ・全検索語・全日付で一致すること、Workerの正規化が `title_key` と3,000件余りの題名（全角・BOM・制御文字・ギリシャ文字の語末のΣなどを含む）で一致することを確かめる。わざと壊すと落ちることも確認した。
- **探せる公演。** 索引の候補の公演（`rec_stage`。これからの公演と、最近まで上演していた公演）だけ。**持ち主の購入メールから作った過去の記録（`credits.jsonl` の件名など）は検索に出さない**（ほかの利用者に持ち主の観劇歴を見せないため）。古い公演を探せるようにするには、公開の公演情報から別に一覧を作る必要がある。
- **D1の書き込み行数。** 無料枠は1日10万行。索引を入れ直すと全行を書き、古い版を消すときにもう一度数える。`--stats` の `rows_written` が目安。

| 確認すること | 方法 |
|---|---|
| 実カタログでの断片の行数と書き込み行数 | EC2で `build_recommend_index.py --stats` の `gram_rows`・`rows_written` |
| 結び付けたあと、おすすめが出る | 本番で、◎と×の記録をそれぞれ公演に結び付けて「あなたへのおすすめ」を見る |
