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
