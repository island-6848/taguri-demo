# 完全移行の独立テスト結果

テスト担当による変更後の正式検証。統括担当の実装freeze完了・開始指示を受けた後に実行した。**実装修正後のローカル37件は全件成功。ただし実Workers環境・実データ移行・画面比較が未検証のため、本番切替を可と判定しない。** 最終レビューはこの試験完了報告の後に別担当が行う。

## 対象と実行環境

初回freeze: 25ソースファイル。`/tmp/taguri-implementation-freeze.json` のSHA256を独立照合し変更なし。manifest SHA256: `72b41681934e561599510333c36fd3f879ea907a07d5cb4b240fcae3d439ea0a`。テスト担当は実装コードを変更していない。

Node v24.19.0、Python 3.12.14、実SQLite SQLを実行するfakeD1、合成A/B利用者と非empty公開カタログを使用。全テストはローカルで、実利用者・公開DBを変更していない。

## 修正後の正式再検証結果

| 検証群 | 件数 | 成功 | 失敗 |
|---|---:|---:|---:|
| 既存JS | 13 | 13 | 0 |
| 運営移行runner独立JS | 3 | 3 | 0 |
| 既存Python変換 | 4 | 4 | 0 |
| snapshot独立Python | 5 | 5 | 0 |
| 認証・統合独立Python | 5 | 5 | 0 |
| 元renderer独立Python | 5 | 5 | 0 |
| 保護旧DB・移行独立Python | 2 | 2 | 0 |
| 合計 | 37 | 37 | 0 |

全17fragment APIは非empty公開カタログで200・本文ありを確認した。17回の呼び出しは表のrenderer test case 1件内で実行しており、件数へ二重加算していない。

初回実行は37件中35成功2失敗。原因は、公開snapshotビルダーが出演クレジットの名前配列を許可・保存する一方、元rendererの`split_names`が文字列を要求するため、非emptyおすすめ表示で500になること。合成入力 `fields={"出演":["検証出演者"]}` をビルドした結果で再現し、統括担当へ報告済み。地域絞り込みの検証もこの500で失敗する。元仕様の地域変更queryは`f=1&pref=大阪府`で、テスト側をこの契約へ補正した。

実装担当が出演者配列を元仕様の文字列へ「、」で連結する修正を行い、freeze-v2を通知。その後source/public snapshotを再ビルドし、全37件の回帰を正式再実行して成功した。単一既存文字列の同値、複数名の連結、未知role除外も確認した。freeze-v2の25ソースSHA256は一致、manifest SHA256は `825eee243167da21384892e7d1e16fe0968437c40b06d944526bc92fcf3242ad`。

## 確認できた内容

- 全列・BLOB・NULL・同内容の重複行・複数回観劇のsnapshot往復一致、A/B所有者の混入拒否。
- 96記録のsnapshot save/loadが50query以内、CAS競合の敗者が成功した変更を上書きしない。
- 新規empty guest、本人復旧、期限付き6桁端末追加の一回使用、改変user_idを無視した本人削除とBの維持。
- 期限切れnative Cookie・未移行旧Cookieで本人と無関係の空利用者を作らない。
- 旧Base32復旧はsecret pepperと運営投入identity mappingがないと503、正しい合成secretとmappingがあれば本人へ戻る。DBには復旧コードhashだけを保存。
- 外部Origin、SQL文字列、不正復旧入力、試行回数超過の拒否。
- native96件を原worksへ変換し、source全列・元ID・timestamp・感想をarchive。再実行は冪等。
- 原POSTの公演追加→作品単位評価→感想→回別メモ、本人全snapshot JSON出力一致。不正評価後のtablesが不変。
- READY=falseは503。正常拒否・例外の運用ログにCookie・URL token・例外の秘密/SQL文字列が含まれない。
- 公開劇場・ツアー劇場・価格・販売情報・出演を保持し、未知credit roleやその私有文字列を除外。
- 運営runnerはsecret未設定404、誤key401、任意SQL拒否。同identity auth投入は冪等、別identity衝突は全transaction rollback。
- 保護旧DBを読取専用でAだけ全列export、sourceファイルhash不変。共有secret表はinventoryのみ。owner localや異なるtargetへのmergeを拒否。途中SQL失敗ではusers/accountsもrollback。

## 未検証・環境上の阻害

- CPython実Handlerを元フロントへ接続する34view（17画面×1280/390px）のブラウザ試験を準備したが、sandboxで127.0.0.1のsocket作成が`PermissionError: [Errno 1] Operation not permitted`となり起動前に停止。見た目の一致を確認済みとは扱わない。再試験でHTTPserverを使わないinterception案を検討したが、Chromium自体の起動がcrashpadの `setsockopt: Operation not permitted` によりSIGTRAPで停止することも確認した。追加権限要求や制限の回避はしていない。
- uv syncを含むネット依存のsetup toolが長時間保留になり中断。統括担当が環境準備を引き継いだ。**実Python Workers/workerd/DOでの実行は、この時点では未確認。** CPython/fakeD1合格はその代わりにならない。
- 実稼働DB・auth DB・pepper・実カタログ・ポスターの安全な提供がないため、全実利用者の移行件数/内容照合と旧認証の実環境互換は未確認。
- 公開Cloudflareで再デプロイ後の永続性、バックアップ復元、DO CPU/無料枠、集中アクセス時の待ち時間、カタログ更新・全画像配信は未確認。
- 一般利用者の全POSTルートを網羅する操作試験は未完。owner専用のGmail/LLM更新を一般利用者へ公開する試験は対象外。

## 再現

依存syncを終えた後にsource/publicビルドを行う。sourceビルド後のpywrangler syncはmoduleを消すため行わない。

```sh
python3 cloudflare/scripts/build_python_bundle.py
python3 cloudflare/scripts/build_public_snapshot.py \
  --catalogue cloudflare/test/synthetic-public-catalogue.jsonl \
  --approved-base-recommendation cloudflare/test/synthetic-public-base.json \
  --output cloudflare/python/python_modules/public_snapshot.py
cd cloudflare
python3 -m unittest discover -s test -p 'test_*.py' -v
node --test --test-isolation=none test/*.test.js
python3 test/browser_migration_check.py
```

browserはローカルsocket許可が必要。CPython entry試験はworkers Response/DOの境界だけをstubしており、workerd対応を証明しない。合成公開fixtureを使ったテスト出力を実本番カタログへ置き換えて公開しない。

修正後の正式実行ログ: [Python v2](test-evidence/2026-10-12-python-tests-v2.log) と [JavaScript v2](test-evidence/2026-10-12-js-tests-v2.log)。初回の失敗証跡も [Python](test-evidence/2026-10-12-python-tests.log) と [JavaScript](test-evidence/2026-10-12-js-tests.log) に保持している。

テスト担当の正式試験はここまで完了。残る未検証項目を含め、統括担当が別のレビュー担当へ最終レビューを依頼する。ローカル成功を完全移行・本番稼働の完了と読み替えない。
