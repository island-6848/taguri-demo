# owner完全移行補完・独立正式テスト結果

作成日: 2026-10-13。実装完了と統括担当のfreeze-v3開始通知の後に、別のテスト担当が正式検証した。実装sourceは変更していない。

**ローカル40件が全件成功。ただし実Workers/DO、公開の実データ移行、画面比較が未確認なので、本番完全移行やRender停止の可否とは別判定。**

## 対象

freeze-v3: 29ファイル、manifest SHA256 `4862c0c928fd95e432f47320041047c184e5e5961bbcde71fab163665c7c1c1c`。独立照合で全file hash一致。

Node24.19.0/Python3.12.14、実SQLite SQLを使うfakeD1と合成owner/guest。ネットワーク追加権限を要求せず、本番DB・実利用者は変更していない。

## 結果

| 項目 | 件数 | 成功 | 失敗 |
|---|---:|---:|---:|
| Python既存変換・snapshot・auth・renderer・protected移行 | 21 | 21 | 0 |
| owner移行Python追加 | 2 | 2 | 0 |
| JS既存・運営移行runner | 16 | 16 | 0 |
| owner runner追加 | 1 | 1 | 0 |
| 合計 | 40 | 40 | 0 |

既存37件の回帰を含む。非emptyカタログで元17APIの200と本文を確認する試験も合格した。

### owner補完の確認

- `local`移行は明示owner-transferとprivate targetを指定した時だけ可能。フラグなしlocal、guestをowner-transfer扱い、guestの異targetへのmergeは拒否。通常guestは同IDを保持。
- ownerの全user_idテーブルの所有値をtargetへ割当し、複合PK由来rowkey、全列checksum、件数を投入後読戻して一致確認。BLOBを含み、元DBファイルhashは変わらない。
- 元checksumとtarget checksumを区別し、共有表はinventoryだけ残す。共有表本文をmanifestへ混入しない。
- 既存targetへの再投入はtransaction全体が失敗し、users/snapshot/rowsは不変。owner runnerも同様に再投入409とtarget不変を確認。
- 復旧コードは別credentialファイルだけに保存。manifest・stdout・stderrに生コードがなく、usersに対応するSHA256だけを渡す。
- manifestとcredentialは0600。再実行で既存ファイルを上書きしない。credentialファイルが既存の場合、新たに作った空manifestを取り除き、既存credentialは不変。

### 新checkout相当の手順

既存生成`python_modules`を退避し、生成物なしからCIと同じsource/public buildを実行して23 Python試験を成功させた。旧生成物は`/tmp/taguri-v3-preexisting-modules`に保持し、sourceは編集していない。83元Python modulesと合成公開カタログを構築するため、手元に偶然残ったbundleへの依存ではない。`uv.lock`も存在する。

## 未検証・制約

- 実Python Workers/workerd/DOの起動と本番API動作は未検証。新CIのbuild追加もローカルで同じ手順を確認しただけで、GitHub上の実行成功は未確認。現CIのruntime smokeとvisualは従来JS/bridge版であり、Python DO成功の証拠ではない。
- ローカルブラウザはChromiumのsocket権限制約で起動不可。PC/スマホ34画面の元デザイン差分は未検証。
- 実DB、auth DB、pepper、私有設定JSON、共有表、実カタログ/推薦/ポスターの全件照合は未検証。owner user_id表だけの変換を全実データ移行完了と扱わない。
- 公開再デプロイ、バックアップ復元、無料枠CPU/DO/D1使用量、同時利用の待ち時間、全POST操作・全画像・更新バッチは未完。
- ファイル作成衝突時のcleanupは検証した。ディスク満杯や書込み途中障害までの復元性は未検証。

## 証跡・再現

[Python v3ログ](test-evidence/2026-10-13-python-tests-v3.log)、[JavaScript v3ログ](test-evidence/2026-10-13-js-tests-v3.log)。旧v2結果と初回失敗証跡は前日の文書に保持する。

```sh
python3 cloudflare/scripts/build_python_bundle.py
python3 cloudflare/scripts/build_public_snapshot.py --catalogue cloudflare/test/synthetic-public-catalogue.jsonl --approved-base-recommendation cloudflare/test/synthetic-public-base.json --output cloudflare/python/python_modules/public_snapshot.py
python3 -m unittest discover -s cloudflare/test -p 'test_*.py' -v
cd cloudflare
node --test --test-isolation=none test/*.test.js
```

依存同期が必要なWorkers実行では、依存syncを先に行い、source構築後に再syncしてbundleを消さない。syntheticカタログは本番公開用ではない。

最終freeze-v4: 29ファイル、manifest SHA256 `341f7c4d268378152e765da4c052796fafc80290d72cc119a2e1e58c44b1cdcd`。独立照合で全file hash一致、v3との差は `.gitignore` のみ。実行code不変のため40件を再実行せず、元ignore仕様の静的検証を追加した。独立一時Gitリポジトリで `.env`、data、pyc、__pycache__、.venv、python_modules がignoreされ、`cloudflare/python/uv.lock` はignoreされないことを確認した。

独立テスト担当の正式検証は完了。未検証事項を含め、統括担当から独立レビュー担当へ最終レビューを引き継ぐ。
