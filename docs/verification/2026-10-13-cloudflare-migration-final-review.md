# 完全移行の独立最終レビュー

> **最新判定は末尾の「freeze-v4再レビュー」を参照。** v2の指摘は履歴として保持し、owner移行工具とlock追跡の補完後の判断を区別する。

担当: review / 作成日: 2026-10-13（日本時間）

統括担当から実装freeze-v2、変更後の独立テスト完了の通知を受けた後に実施した。順序は **実装完了 → 変更後テスト完了 → 本レビュー**。元仕様の事前調査とは区別する。実装コードは編集せず、ネットワーク接続・公開DB操作・新しい権限要求は行っていない。

## 判定

- **ドラフトコードの公開: 可。** 試作であること、下記の未完了事項を明記し、別Worker・別DB・`MIGRATION_READY=false` を保持する。依存lockを公開対象に含める。
- **本番切替・Render停止: 不可。** 実ランタイム、実全件移行、持ち主データの経路、全操作・見た目・復元・性能の確認が足りない。現行本番の `ORIGINAL_UI_BRIDGE=true` を維持する。
- **完全移行完了: 未達。** 元画面を再利用する移植コードと保護された移行工具ができた段階。ローカル37件成功を公開環境での完全移行成功とは扱わない。

## 対象と証拠

[独立テスト結果](2026-10-12-cloudflare-migration-test-results.md)、[元の移行要件](2026-10-12-cloudflare-migration-and-onboarding.md)、[実装記録](2026-10-12-cloudflare-migration-execution.md)を照合し、元Python、Python移行入口・認証・snapshot保存、運営runner、公開素材builder、JSログ、元フロントの変更を読んだ。

freeze-v2は25ファイル。manifest SHA256は `825eee243167da21384892e7d1e16fe0968437c40b06d944526bc92fcf3242ad`。レビュー時に全25ファイルのSHA256を照合し、変更・欠落はなかった。テスト担当の証跡はPython21件・JS16件、計37件成功。17fragment APIの200確認はその中の一つの試験に含まれる。

## 要件との差・切替阻害事項（重大度順）

| 重大度 | 指摘・再現条件 | 根拠と必要な対応 |
|---|---|---|
| P0 | 公開URLの処理・保存はまだRender。現行設定のままRenderを遮断すると元画面が使えない | [現行設定](../../cloudflare/wrangler.jsonc) は `ORIGINAL_UI_BRIDGE=true`。別の [Python設定](../../cloudflare/python/wrangler.jsonc) はDB placeholder・READY=false。実データと検証完了後に切替が必要 |
| P0 | Python Workers / Durable Object / 実D1で実行できることを未確認 | [入口](../../cloudflare/python/entry.py) はDO、JS境界、SQLite、仮想ファイル、scryptを使う。CPythonとfakeD1での成功だけでは互換性を判断できない。実workerdで全経路・依存・DB境界を確認する |
| P0 | 実利用者の全件データ・認証・公開素材の移行を実施していない | 旧DB/auth DB/pepper/素材の保護された提供、全表全列・件数・内容・checksum照合、最終差分移行、移行前バックアップと別DBへの復元が必要 |
| P0 | 持ち主 `local` のデータは移行対象から明示除外される | [prepare_legacy_migration.py](../../cloudflare/scripts/prepare_legacy_migration.py) 27–29行、[legacy_runtime.py](../../cloudflare/python/legacy_runtime.py) 123–129行。`user_id=local` の準備/画面実行は拒否。これは誤公開防止として妥当だが、持ち主の完全移行経路は未実装。本人確認・移行先ID・購入由来の全観劇回・共有表の扱いを別途実装する |
| P0 | 元の見た目と全操作の同等性を確認できていない | 34viewのブラウザ試験は環境制限で未実行。17画面200・本文ありは、全ボタン・HTML断片更新・D3・ナビゲーション・PC/スマホ同等性の証明ではない。一般POSTを網羅して元版の入出力・保存直後の再表示と比較する |
| P0 | 再デプロイ耐久、切り戻し、無料枠と利用者の待ち時間を未確認 | [entry.py](../../cloudflare/python/entry.py) 172行は全利用者を一つのDOへ送る。CPU・D1走査行/書込行・容量・集中時の待ち時間・画像とカタログ更新を実測する。無料対応であることと無料枠で継続できることを区別する |
| P1 | 本人書き出しの再取り込み・復元用UI/APIがない | JSON/ZIPは本人snapshotの出力に改善された。一方、Python移行版は旧native APIを409にし、一般ユーザー向けsnapshot再取り込みは接続していない。運営runnerは新規account投入であり、本人の復元導線ではない。安全な形式検証と本人限定の復元を追加する |
| P1 | 依存lockの公開漏れで新しい環境の準備が失敗し得る | [.gitignore](../../.gitignore) 5行は `cloudflare/python/uv.lock` を除外。一方 [run_python_preview.py](../../cloudflare/scripts/run_python_preview.py) は `uv sync --locked` と `workers-py==1.17.7` を要求する。freezeにはlockがある。公開commitにlockを明示追加し、新規checkoutから再現を確認する |
| P1 | 一般運用に必要な上限・認証継続の方針が未確定 | 100アカウントのpreview trigger、30日セッションを保持している。登録停止はPython経路では統一されるが、本番旧bridgeには別の登録経路がある。公開人数、期限切れ案内、実利用とデモの区別を実設定で検証する |

P0は切替前の必須条件。P1も一般利用者へ継続運用を案内する前に解消・運用方針を確定する。**本人snapshotの再取り込みUIは元の公開UIにはない追加受入条件**であり、元機能を失ったという指摘ではない。先に提示した移行検証文書の「書き出しと再取り込みで本人の全記録が欠損なく戻る」と、継続運用時の復元条件に対応するP1として扱う。新規確定の実行時不具合として報告するものはないが、上記の未実装・未検証を成功とは扱わない。

## 既存機能への影響

- 元の17画面生成関数・一般操作を再利用する方針は要件と一致。評価・感想は作品単位、`visit_note` は回別の非推薦メモ。同日昼夜の券は日付＋時刻で区別する。回別評価への勝手な変更をしていない。
- snapshotはuser_id付き全表全列を保持し、CAS付き単一batchで変更行だけを保存する。旧共有表は自動コピーせずinventoryへ残す。購入原本・共有素材・画像等を取得しないまま全データ保持とは言わない。
- native D1の記録は元形式へ一度だけ変換し、元列をarchive・元表を保持する。切替後は古いnative変更APIを止める実装があり、片側だけ保存される双方向運用を避けている。
- `local` 拒否、公開demoでのowner-onlyメール/LLM処理・画像編集の制限を保持する。各利用者向けGmail OAuthを追加済みとは扱わない。
- 元デモの共通推薦順位を承認済み公開データとして使う方式。個別ユーザーの評価による新しい独立再計算を実装済みとは記載しない。
- 現行Render経路では削除カードを追加せず、persistent_modeの応答でだけ説明・削除導線が変わる。見た目の影響は未実行ブラウザ試験で確認が必要。
- JSON/ZIPの全ユーザー出力を復活させず、本人snapshotだけへ限定した点は妥当。ZIPに認証DB・セッション・他アカウントを混ぜない。

## ログと秘匿

[operation-log.js](../../cloudflare/src/operation-log.js) はイベント、許可リストの操作名、method、status、所要時間、backendのみ。未知pathをそのままログへ出さない。[entry.py](../../cloudflare/python/entry.py) も固定route種別と所要時間を記録し、想定外の例外message/tracebackを応答・ログへ出さない。

生Cookie、復旧コード、URL query、本文、メール、感想、ユーザーID、SQL、pepperをログへ追加する変更は確認しなかった。テストで例外の秘密文字列が出ないことも確認されている。既存のowner処理を一般公開しない条件を保持する。実プラットフォーム側ログのアクセス権・保管期間・出力設定は運用時に確認する。機能ログの追加を根拠に、プラットフォーム側を含めた全秘匿確認済みとは言わない。

## テスト不足と次の受入条件

1. 実Python Workers / workerd / DOでビルド・起動・全ルート・JS binding・scryptを検証する。
2. 17画面×PC/スマホの比較と操作試験を実行。反応によるカード補充、券の時刻、設定の順位変化、統合/解除/除外/復元/完全削除、手動クレジット、D3分析を含める。
3. 新旧の利用者と持ち主を分け、実全件の件数・内容・関連付け、旧Cookie/復旧コード、nativeコードの到達を照合する。
4. 利用者間分離を読むだけでなく、全変更ルート・出力・削除・復元で確認する。JSON/ZIP出力後の本人再取り込みも実装・確認する。
5. 実D1でCAS競合、rollback、無料query/binding上限、read/write行数を測る。fakeD1の50query内という結果だけで実課金計上の同等性を判断しない。
6. 本番相当で再デプロイ、Cookie期限、端末追加、バックアップ復元、Render遮断、切り戻し、公開画像・カタログの更新を確認する。
7. 依存lockを含む公開差分を検査し、新しいcheckoutからビルド手順を再現する。

修正が必要な場合は実装担当へ戻し、再凍結 → テスト担当の変更後再検証 → レビュー再確認の順で進める。本レビューで実装変更は行っていない。

## freeze-v4再レビュー（現在の判定）

実装担当のowner補完完了、独立テスト担当の正式テスト完了の通知後に再レビューした。対象29ファイルのSHA256を独立照合し、全てfreeze-v4と一致した。manifest SHA256: `341f7c4d268378152e765da4c052796fafc80290d72cc119a2e1e58c44b1cdcd`。実装コードは変更していない。

[10月13日の独立テスト結果](2026-10-13-cloudflare-migration-test-results.md)はPython23件・JS17件、計40件全成功。v3からv4への変更はignore設定だけで、実行コード不変のため、追加の静的ignore検証と既存40件の証跡を確認した。

### 解消したv2の指摘

- **localのuser_id付きDB移行工具は補完済み。** [prepare_legacy_migration.py](../../cloudflare/scripts/prepare_legacy_migration.py) は明示 `--owner-transfer`、新しい非localのtarget、別の復旧credential出力を要求する。全所有値を書き換え、複合PKのrowkeyとtarget checksumを再計算し、元checksumも残す。runnerの明示owner opt-in・既存target衝突のrollbackと整合している。通常guestの異IDへの移行・暗黙mergeは拒否する。
- ownerの新コードは別0600ファイル、manifestはSHA256だけ。stdoutへ生コードを出さず、既存ファイルを上書きしない。移行先は非localであり、元のowner-onlyメール・LLM・編集権限は継承しない。この権限分離は妥当。
- **lock追跡の問題は解消済み。** `.gitignore` は元の `.env` / `data/` / bytecode除外を保持し、生成vendor/venv/public snapshotを除外する一方、uv.lockは除外しない。公開commitにlockを含める条件を満たせる状態となった。
- CIは生成物のない状態からsource bundleと合成公開素材を構築する工程を追加した。独立テストも同じ手順をローカルで確認しており、残存bundleへの依存を減らした。CI上の実行結果は別途確認が必要。

### 残る要件差・影響・テスト不足

1. **P0: 実環境と切替は未実施。** 本番Bridge=true、Python READY=false/別DB placeholderのまま。Python Workers/DO/実D1、全実データ照合、再デプロイ、Render遮断、復元・切り戻し、性能・無料枠は未確認。40件成功でこれらを代替しない。
2. **P0: owner全データの完全移行は未完了。** 今回の補完はuser_id付きDB表の転送。購入由来の観劇回、私有JSON/設定、共有表、カタログ・推薦・画像はinventory/別準備のまま。実取得・明示変換・内容照合が必要。owner工具補完を、持ち主全データの移行完了と表現しない。
3. **P0: 全操作・見た目の同等性は未確認。** 全17fragment APIの200は確認済みだが、一般POST全件・34view比較・D3/カード更新・削除等の元フロントとの動作は未完。新CIの従来JS/bridge用runtime/visualはPython DOの動作証明ではない。
4. **P1: 本人再取り込みは未実装。** 元UIの機能を失ったという指摘ではなく、先の検証MDで提示した継続運用・復元の追加受入条件。運営の新規投入runnerと区別する。
5. **P1: 一般公開の上限・期限方針を確認する。** 100人preview、30日session、登録停止、新規empty guestを実公開設定で確認する。単一DOへの集中時の待ち時間も測る。
6. owner credential/manifestの書込み途中障害（ディスク満杯等）の復元性は未検証。生成前の保護バックアップを保持し、両ファイル完成・hash/件数照合を確認してから投入する。コードに新たな秘密ログの露出は認めなかった。

**最新判定: ドラフトコード公開は可。本番切替・Render停止・完全移行完了の判定は不可。** v2で挙げたowner工具未実装・lock追跡不足は上記の限定範囲で解消した。新たな確定実行時不具合は見つからなかった。実環境未検証を理由に本番切替ゲートを維持する。
