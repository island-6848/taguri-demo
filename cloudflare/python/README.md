# 元UIを保持するPython Workers移行版（本番切替は検証後）

元 `serve.Handler` の17画面fragment APIと操作を同期実行し、各要求専用SQLiteをD1に永続化します。元HTML生成関数を再利用し、別UIは作りません。この設定は現行本番Workerとは別名・別DBです。軽いWorker入口からSQLite-backed Python Durable Objectへ元rendererと認証を委譲し、D1を永続データの正とします。DO storageに個人記録は保存しません。Workers Free対応のDO・既定30秒CPU枠を使い、有料CPU設定は追加しません。

## 実装

- `legacy_runtime.py`: 元の一時地域絞り込みは `app_setting.runtime_pref_filter` として本人だけのsnapshotに保持し、別要求でも継続します。設定画面の既定地域を保存すると元ハンドラーの `set_prefs` 経由で現在の地域も同時に更新します。Socket・監視スレッド・subprocessを起動せず元renderer/controllerを実行。各要求のDB参照とキャッシュを必ず復元。失敗操作は保存せず、管理者専用操作の権限を維持。承認済みbundleがなければ元の私有ディレクトリへフォールバックしません。
- `snapshot_store.py`: 全user_idテーブル・全列を保持し、アカウント単位revisionのCASをD1の単一batchで処理。主キーに基づく変更行のみを `json_each` でまとめ、read-only要求は保存しません。保存は最大40 SQL・各binding 900KB以下（認証等を含むWorkers Freeの50query上限には実測も必要）。`presented` は各アカウント内の保存表へ所有列を付加。
- `entry.py`: 原画面API・原認証ページ・認証POST・Cookie・個別JSON/ZIP書き出し・公開ポスター・運用ログを接続。旧migration APIの変更は409、旧migration-data画面は元UIへ案内。設定の既存card形式にアカウント削除導線を追加。
- `cloud_auth.py` / `native_provision.py`: 端末追加・復旧・新規empty guest・個別削除、ネイティブD1プレビュー記録の全列アーカイブ＋原形式への一度だけの変換。
- `schema.sql` / `auth-schema.sql`: 新規snapshot/auth補助テーブル。現行本番migrationへ追加していません。
- 元フロント `app.js` は `persistent_mode` の場合だけ復旧コード・保存の説明を変更します。既存Render経路の文言・レイアウトは保持します。

## ビルド

リポジトリのルートで実行します。

```sh
python cloudflare/scripts/run_python_preview.py \
  --mode build \
  --catalogue /安全な場所/承認済み公開カタログ.jsonl \
  --approved-base-recommendation /安全な場所/既公開の共通推薦.json
```

`--mode dev` または `--mode deploy` も同じ準備を済ませてから直接Wranglerを呼びます。`--poster-dir` は任意です。`deploy` は独立preview DBのplaceholderが残っている場合に拒否します。本番切替を行う脚本ではありません。

順序は **`uv sync --locked` → `uv run --no-sync pywrangler sync --force` → 元source bundle構築 → 承認済み公開snapshot構築 → `npx --no-install wrangler dev/deploy`** です。`uv.lock` の `workers-py==1.17.7` を固定します。この版の `pywrangler/sync.py` はvendorディレクトリを削除して依存packagesをコピーし、`pywrangler dev/deploy` 自身もsyncするため、source構築後にこれらを呼ぶと同梱sourceが消えます。sourceを構築してから再syncしないでください。ツールを更新する場合は、この挙動を確認して脚本のversionチェックも合わせて更新します。

元sourceの `.py` と既公開96件fixtureを `python_modules/taguri_project/tools/...` の同じ階層へ同梱します。`data`・DB・auth・pepper・メール・owner私有JSONのディレクトリはコピーしません。公開カタログ/クレジット/題材はホワイトリストで再構成し、未知credit roleは落とします。既知の衣裳・舞台監督・宣伝美術を保持し、推薦cardとtour会場は構造ごとのホワイトリストで劇場・日程・料金・発売状況・元会場IDを残します。必要な役職は `build_public_snapshot.py` の `PUBLIC_FIELDS` に明示追加します。公開ポスターは `--poster-dir` と `--assets-dir cloudflare/public` を明示した場合のみ、カタログのstage IDと一致する検証済み画像を同梱します。

元推薦の順位は持ち主の記録から作った全員共通のものという原仕様を保持します。`--approved-base-recommendation` は**すでに公開され承認済みの原一覧**だけを渡します。感想引用・ownerお気に入り・メール等は同梱しません。各利用者の◎から独立した推薦を再計算する実装ではありません。元一覧がない場合に順位を捏造せず、入口は準備未完の503を返します。

Python版の起動・公開には上記脚本を使い、最後の工程は直接Wranglerを使用します。公開前に `wrangler.jsonc` の独立preview DB IDを設定し、そのDBへ `../migrations/0001.sql`、`../migrations/0002.sql`、`schema.sql`、`auth-schema.sql` の順で適用します。本番DBへ試作schemaを直接適用しません。

## 本番切替ゲート

**実装が存在することと、完全移行の検証完了は異なります。`MIGRATION_READY=false` を維持します。**

1. 原版の実DB・認証DB・pepper・ポスター/カタログ等の保護されたバックアップ取得と、全テーブル全列の移行照合。
2. 旧Render Cookie/復旧コードの保護された移行。現補助mappingだけで全旧コード互換を保証できません。詳細は `AUTH-CONTRACT.md`。
3. Python Workers上の依存解決・同梱source・SQLiteの実行、全画面/一般操作/ユーザー分離/競合CAS/復旧/端末追加/削除の独立テスト。
4. 実データでWorkers FreeのCPU・D1クエリ/row/binding・read/write・画像/モジュール容量の実測。CPythonで17画面が描けても、Durable Objectの30秒CPU・無料request/duration枠で継続できる証拠にはなりません。単一DOへの集中時の待ち時間も計測します。
5. 原公開カタログ・原共通推薦・ポスターの承認済みsnapshot。再取得・更新は運営のバッチとして管理し、一般利用者に管理者のGmail/LLM操作権限を渡しません。
6. 同じ識別子の旧native APIへの書込みを停止してから切替。変換は一度だけなので双方向同時保存はしません。

## 非破壊バックアップ

```sh
python cloudflare/scripts/export_legacy_account.py \
  --db /安全な場所/ratings.db --user-id 対象ID --output /安全な場所/backup.json
```

読み取り専用・一貫したSQLite読取transactionで、全user_idテーブルの全フィールド・件数・SHA256を保存します。既存ファイルを上書きせず、保存先は0600。共有表は名前/列の一覧のみで自動コピーしません。auth DBとpepper、画像・公開カタログ等は別途保護したバックアップが必要です。出力には個人記録が含まれるためGitへ追加しません。ZIP書き出しは利用者のJSON snapshotだけを含み、元の他利用者込み全data.zipを復活させません。

公式制約: [Python DO](https://developers.cloudflare.com/changelog/post/2025-05-14-python-worker-durable-object/)・[DO CPU](https://developers.cloudflare.com/durable-objects/platform/limits/)・[DO無料枠](https://developers.cloudflare.com/durable-objects/platform/pricing/)・[D1制約](https://developers.cloudflare.com/d1/platform/limits/)。無料枠内なら追加料金不要という設計であり、無制限・永久無料を保証しません。

## 実データをD1へ投入する手順（運営のみ）

1. 上記snapshot/authの補助schemaを**独立preview DB**へ作る。
2. 読み取り専用の保護された旧DBから、同じ利用者IDを明示してbatch manifestを生成する。

```sh
python cloudflare/scripts/prepare_legacy_migration.py \
  --db /安全な場所/ratings.db --user-id 旧利用者ID \
  --target-user-id 旧利用者ID --output /安全な場所/account-batch.json
```

3. `migration-runner.wrangler.jsonc` の独立DBを設定し、秘密管理から十分長い `MIGRATION_ADMIN_KEY` を設定した運営限定runnerの `POST /import-account` へ送る。認証は `Authorization: Bearer <秘密>`、本文はmanifest。秘密・本文をコマンドログやGitへ載せない。既定 `workers_dev=false` で公開入口はなく、secret未設定なら404。
4. 原認証DBと明示した同ID mappingから `export_legacy_auth.py` のJSON manifestを生成し、同runnerの `POST /import-auth` へ送る。本人ID・target snapshotが一致しない場合は拒否。原sessionの生tokenは送らずSHA256だけを使う。pepperは公開assetに入れず、必要ならPython DOのsecretとして別途設定する。
5. 全表・全列・件数・checksumを読戻して照合する。旧snapshot/既存nativeと同じIDに無理に上書きしない。一般閲覧者の旧IDは同じIDへ移し、異なるUUIDへの暗黙mergeを拒否します。持ち主 `local` は以下の明示的な運営専用経路だけで、新しい非local本人IDへ移します。

account manifestは `users` と全snapshot rowsを**D1.batchの単一原子transaction**へ渡します。既存account/snapshotと衝突すれば全体をrollbackし、暗黙merge/上書きしません。SQLファイルを複数回 `d1 execute` して部分的に投入する方式ではありません。runnerは固定のaccount/auth生成SQLだけを受理し、任意SQL endpointは用意しません。authも同じIDは冪等、異なるidentity衝突は全batch失敗です。共有表・公開素材・owner専用分析は自動copyせず別照合のままです。入力manifestは0600・既存file非上書きで保存し、runnerはschema/rowサイズ・最大40queriesを検査します。

## 持ち主localの本人データ移行（運営だけ）

```sh
python cloudflare/scripts/prepare_legacy_migration.py \
  --db /安全な場所/ratings.db --user-id local \
  --target-user-id 新しい本人用ID --owner-transfer \
  --output /安全な場所/owner-batch.json \
  --owner-recovery-output /安全な場所/owner-recovery.json
```

新targetは未使用の非local IDを明示します。既存guest/native利用者へ上書き・mergeしません。targetが既に存在すると運営runnerのD1.batch全体が失敗し、既存記録は保持されます。元DBは読取専用です。全private tableの行のuser_idだけをtargetへ置換し、複合主キー由来のrow_keyと移行先SHA256を再計算します。manifestはsource SHA256も残します。列・NULL・BLOB・観劇回数・感想等はそのまま保持します。

本人の新64桁復旧コードは別の指定ファイル(mode600)だけへ一度保存し、manifestにはhashのみ、stdout/logにはコードを出しません。元authのusers.recovery_hashや別利用者のcredentialは変更しません。localは旧scrypt guestアカウントではないため、legacy_user_map/legacy_sessionへ勝手に追加しません。新しい本人IDは通常Web利用者であり、元local限定のGmail/LLM・所有者分析・外部プログラム実行権限を受け取りません。

**この経路だけで完全移行とは判定しません。** user_idのない共有表はinventoryに残り、移行しません。元のdeclared/declined JSON、購入メール、共有素材、分析入力等もこのDB工具では自動移行しません。本人だけの設定として取り込む要否と対応を別途照合し、全inventoryを説明できるまで完全移行ゲートを維持します。私的ownerデータを共通公開推薦へ混入させません。

CIは新規checkoutで合成公開fixtureとsource bundleを生成してから独立Python試験を実行します。生成物はGitへ追加せず、`uv.lock` の依存pinは追跡します。合成fixtureを本番の公開入力へ置き換えてデプロイしません。
