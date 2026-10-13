# 認証アダプターの接続契約

- `cloud_auth.handle_auth(request, env)` は先に呼ぶ。戻り値は `(status, JSON辞書, headers)` または `None`。`/api/recover` と `/api/link/redeem` の URLencoded 入力には既存の認証ページと成功リンクを表示し、JSON 入力には辞書を返す。元UIの `/auth/start`、`/recover`、`/link` ページは入口担当が再利用する。
- 通常の元UI APIには `resolve_account(request, env)` を呼ぶ。`user_id`、一度だけ返る `welcome_code`、任意の `set_cookie` を元画面応答に接続する。`welcome_code` は既存 `showWelcomeCode` を動かすレスポンスJSONへ追加する。
- POSTは既存の入口で同一Originを必須にする。認証専用ルートも自分で検査する。
- `AuthError.status/message` は利用者向けの定型文のみ。想定外例外は内容をレスポンスにもログにも出さない。
- `auth-schema.sql` は既存users/sessionsとlegacy snapshot schemaの後に追加する。旧データの変更・削除はしない。
- 既存native cookie・64桁復旧コードは同じusers/sessionsを使う。ネイティブ記録があるアカウントは初回にだけ原形式へ追加変換する。元records/favourites/reactionsを削除せず、全列をsnapshotのnative_sourceにも保存する。
- **原形式へ変換後、旧native APIに書き続ける双方向同期は未実装。切替後は旧migration-dataの変更系APIを明確に止め、同じアカウントの元UIへ案内する必要がある。**古いAPIに成功を返して片側だけ更新する運用は不可。
- 初回の新規guestは空の記録で始まる。既存の期限切れnative cookieや旧tg_sessionがある端末に別の空アカウントを自動発行しない。
- 100人preview登録上限は既存D1 triggerにより維持する。
- 復旧コード・生Cookie・IP・SQL・本文をログに出さない。IPはCF-Connecting-IPのSHA256のみ短期throttle表に保存し、信頼済みCloudflare入口からのservice bindingで渡す必要がある。

## 旧Render認証の移行ゲート

旧復旧コードはpepper付きscryptでuser_idを導出するため、auth.dbだけから旧コードのSHA256を作れない。保護されたPython Durable Object計算経路では、Cloudflare Secret `LEGACY_AUTH_PEPPER`（元32bytesのhex）と `LEGACY_SCRYPT_ENABLED=true` がある場合だけ原方式のscrypt(N16384/r8/p1/dklen16)を実行する。得られた旧user_idは、運営者がバックアップに基づき作成した `legacy_user_map` と既存users/legacy_accountsに一致した場合だけログインする。任意コードから利用者を新規作成しない。本人確認できたコードはSHA256だけを `legacy_recovery` へ追加し、生コード・pepperを保存/出力しない。pepper・mappingが未投入、あるいは実ランタイムのscryptが非対応なら503の移行ゲートを維持する。元pepper・本番バックアップは未入手のため、互換が本番で完了したとは言えない。

`cloudflare/scripts/export_legacy_auth.py` は明示的な旧ID→新D1ID JSON mappingと読み取り専用auth.dbから、旧tg_sessionのSHA256と元created_at基準365日の残存期限のみを固定JSONmanifest（既定）または `--format sql` へ出力する。生セッション・pepper・コードは出力しない。出力は保護ファイル(mode600)。JSONは隔離された管理用runnerが定義済みクエリへ変換しD1.batchで原子的に投入するための入力であり、任意SQLをWeb経由で実行する用途ではない。SQLはD1非対応のBEGIN/COMMITを含めず、既存usersと移行済みlegacy_accountsがないtarget、または既存identity/sessionとの不一致をNOT NULL制約エラーで停止する。一致する再実行は冪等。途中失敗では先行文だけ実行済みになり得るため、原因を診断して同じ入力で再実行し、全mapping/session件数とsnapshotの対応を照合する。SQLファイル実行だけで成功扱いにしない。任意の元cookieを新アカウントへ変換しない。

同一Workersドメインに旧tg_sessionが残る利用者は、ハッシュ移行済みsessionで同じ移行アカウントを確認し、新しいtaguri_sessionと一度表示する追加64桁復旧コードを受け取る。既存のusers.recovery_hashは上書きせず、旧コードも引き続き有効。元RenderドメインだけにあるCookieは別ドメインへ自動移送できないため、旧復旧コードか保護された移行操作が必要。

## 端末リンク・削除

6桁端末リンクは10分、1回限り。D1 `UPDATE ... RETURNING` による原子的消費。発行/利用はIP当たり10分に10回まで。リンク作成時の活性コード衝突は既存コードを上書きせず失敗する。無効な推測の制限はIPバケットで行い、`attempts<5` は行の消費上限であり「間違ったコードを5回」制限ではない。

`POST /api/delete_account` は既存の有効セッション・同一Origin・JSON等の `confirm: "DELETE"` を要求し、そのuser_idのsnapshot/native/authのみ削除する。Python移行入口が設定画面末尾の既存card形式へ削除ボタンを追加し、フロントの明示確認後に接続する。既存Render入口にはこのカードは追加しない。
