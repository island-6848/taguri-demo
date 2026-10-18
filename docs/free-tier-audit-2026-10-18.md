# 無料枠の合算の点検（2026-10-18、issue #139）

> たぐりは有料のものを 1 つも使わない〔dec-free-tier-only〕。この文書は、取得・推薦・管理・バックアップ・再試行など
> **使う側を全部足しても** 各サービスの無料枠に収まるか、そして **使う側のそれぞれが上限の手前で止まるか** を、
> コードと本番の実行の記録から数え直したもの。上限の数字は `cloudflare/scripts/free_tier.py`（`CAPS`）と
> `cloudflare/src/free-tier.js` にだけ書いてある（この文書では引用するだけ）。一覧と守り方は `docs/free-tier-budget.md`。

- 対象: master `2cc2125`（2026-10-18）に、この点検で直した分（下の「直したもの」）を足したもの
- 調べ方: コードの読み合わせ・ローカルの試験（`node --test`・`python3 -m unittest`）・本番の取得の実行（taguri-crawler の Catalog #12）のログ
- 本番で無料枠を使い切る試験はしていない（issue の条件どおり）。提供側（Cloudflare・GitHub）の画面の数字とは突き合わせていない（下の「残したもの」）
- 公式の料金表: この作業環境からは developers.cloudflare.com・docs.github.com を開けない（WebFetch が名前解決に失敗、〔cf-docs-blocked-here〕）。
  **数字はすべて公式ページを検索結果の引用で確かめたもの**〔cf-free-tier-snippets-1018〕

## 1. 本番の今の量（Catalog #12、2026-10-18 04:09 UTC の Free-tier check）

| 項目 | 使った量 | たぐりの上限 | 上限に対して | 無料枠に対して |
|---|---:|---:|---:|---:|
| GitHub Actions（直近 31 日） | 886 分 | 1,500 分 | 59% | 44% |
| D1 の書き込み（その日・取得の分） | 47,547 行 | 80,000 行 | 59% | 48% |
| R2 の保存 | 367 MB | 8 GB | 4.6% | 3.7% |
| R2 の Class A（10 月） | 6,653 回 | 30 万回 | 2.2% | 0.7% |
| R2 の Class B（10 月・Worker と取得） | 1,822 回 | 300 万回 | 0.06% | 0.02% |

**8 割を越えているものは無い。** ただし Actions は、過去の公演とポスターの読み取りが「残りの分を使い切る」作りなので
（`free_tier.plan`）、このまま毎日読むと直近 31 日が 1,200 分（上限の 8 割）を越え、Free-tier check が失敗して通知が届く見込みが高い。
これは上限を越えたのではなく、上限の手前まで使うように作ってあるためで、通知が来ても止める必要はない（起案者に伝える）。

## 2. 合算の表（最悪の日・最悪の月）

「最悪」は、各使い手がそれぞれの上限いっぱいまで使い、同じ日（UTC）・同じ月に重なったとき。

| 枠 | 無料枠（公式） | 越えたとき | たぐりの上限 | 使う側と、それぞれの最大 | 最悪の合計 | 収まるか |
|---|---|---|---|---|---:|---|
| **R2 の保存** | 10 GB-月（口座全体・入れ物の合計） | **請求** | 取得 8 GB・管理画面 0.5 GB（今回足した） | 取得の控え: ポスター・名前の索引（今 69 MB）・控え（taguri-backup）／管理画面の控え: ポスター（月 300 枚）・お試しの文字（10 MB まで） | 8.5 GB | ○（85%） |
| **R2 の Class A** | 月 100 万回 | **請求** | 取得 30 万回（管理画面も同じ数で止まるが、別の控え） | ポスターの PUT とやり直し（今回、やり直しの 1 回ごとに上限を見るようにした）・縮め直し・名前の索引（1 日 256 回まで、月 約 7,900 回）・控え（PUT 1 ＋入れ物の確かめ 2、今回数えるようにした）／管理画面: ポスター月 300 枚・文字 1 回 | 約 30.03 万回 | ○（30%） |
| **R2 の Class B** | 月 1,000 万回 | **請求** | 300 万回（Worker と取得の合計で点検） | Worker のポスター・名前の索引の読み出し（`r2ReadAllowed`、300 万回で止まる）・取得の縮め直し（30 万回まで）・控えの入れ物の確かめ（月 31 回）・戻す予行（月 4 回まで、数えていない） | 約 330 万回 | ○（33%） |
| **D1 の書き込み** | 1 日 10 万行（口座全体。予行の D1 も入る） | その日はエラー（請求なし） | 取得 8 万行・管理画面 1,000 行・予行 1 万行（今回足した） | 取得: 公演一覧 6 万・過去の公演 2 万・ポスター・カード・索引（同じ控えから引く）／管理画面（別の控え）／予行（月 1 日）／定期実行: 空のアカウントの片付け 50 人まで・修正依頼の片付け 500 件ずつ（今回、上限を付けた。前は最悪 約 8,000 行）／利用者の操作（全体の上限は無い） | 取得・管理・予行・定期実行で 約 9.35 万行。残り 約 6,500 行が利用者の分（予行の無い日は 約 1.65 万行） | △ 利用者の操作が多い日は越えうる（止まるだけで請求なし） |
| **D1 の読み出し** | 1 日 500 万行 | その日はエラー（請求なし） | 数えていない | 利用者（見積もり: 300 人で 1 日 約 350 万行、〔q-d1-reads-real〕）・控えの書き出し（利用者の表を 3 回ほど走査）・再生（30 万行 × 2 まで）・片付け（数千行）・見張り | 見積もり 400 万行台 | △ 見積もりだけ。数える仕組みが無い |
| **D1 の保存** | 5 GB（口座の全 D1 の合計） | 書けなくなる（請求なし） | Worker が 4 GB で増える書き込みと新規登録を止める | 利用者の記録・公演一覧・索引・過去の公演（今 48.6 MB）・予行の D1（一時、1 万行まで） | 4 GB ＋取得の 1 日分 | △ 取得の側は大きさを見ずに書く |
| **Workers の要求** | 1 日 10 万回 | その日はエラー（請求なし） | 1 人 10 秒 120 回（全体の上限は無い） | 画面・API・ポスター（静的ファイルは数えない）・見張り 1 日 約 75 回・定期実行 1 日 1 回 | 利用者しだい | △ 止まるだけで請求なし |
| **Workers の CPU** | 1 回 10 ミリ秒（定期実行も同じ） | その回がエラー | 重い図はブラウザで組む・推薦の CPU を減らした（#138） | 定期実行（片付け・修正依頼の片付けは D1 の待ちが中心） | ― | ○（測定は `measure_worker.mjs`） |
| 定期実行（Cron Triggers） | 口座で 5 個 | ― | ― | `41 18 * * *` の 1 個 | 1 個 | ○ |
| 回数制限（Rate Limiting の結び付け） | 無料プランで使える（料金の記載は見つからず〔q-rate-limit-binding-pricing〕） | ― | ― | 要求ごとに 1〜2 回。D1 は使わない。`/api/health` の様子は isolate の中だけ | ― | ○（料金は未確認） |
| **GitHub Actions（非公開）** | 月 2,000 分（口座全体。ジョブごとに分へ切り上げ） | 止まる（支払い方法なし・上限 0 ドル） | 直近 31 日で 1,500 分 | Catalog（plan が決める）・索引だけ（plan）・Replay（plan、20 分）・Restore drill（今回 plan を通すようにした、20 分）・Diagnose（手動、10 分、plan なし） | 1,500 ＋ Diagnose 10 分 × 手動の回数 | ○（Diagnose を 48 回動かさない限り） |
| GitHub Actions（公開の taguri-demo） | 標準の実行環境は無料 | ― | ― | 試験・見張り（毎時）・Pages | 0 分 | ○ |
| Workers Builds | 月 3,000 分 | 未確認 | 数えていない | master に押すたび 1〜2 分（10 月は 1 日 約 19 回） | 月 約 570〜1,180 分 | △ 1 日 50 回押すと越える。数えていない〔q-workers-builds-minutes〕 |
| Gmail（修正依頼の知らせ） | 1 日 500 通 | 送れない | 1 日 30 通 | Worker が送る前に `usage` に数える | 30 通 | ○ |

## 3. 使う側ごとの点検（数えてから使うか）

| 使う側 | 使う枠 | 使う前に共通の数えを見るか | 失敗・やり直しも数えるか | 今回 |
|---|---|---|---|---|
| Catalog の plan（`free_tier.py plan`） | Actions | ○ API で直近 31 日を数える。読めなければ毎日の分だけ | ○ ジョブの実時間を数える | ― |
| 公演一覧（`deliver_catalogue.py`） | D1 書き込み | ○ `d1_left` → `d1_spend`（書く前）→ `d1_settle`（D1 の数に置き換え） | ○ 書く前に足す | ― |
| 過去の公演（`deliver_past.py`） | D1 書き込み | ○ 同上 | ○ | ― |
| ポスター（`deliver_posters.py`） | R2 保存・Class A・Class B、D1 | ○ 1 枚ごと | ○ やり直しも 1 回ずつ数える | **直した**: やり直しの前にも上限を見る（前は上限の 1 回手前から 3 回まで送れた） |
| 名前の索引（`deliver_past_index.py`） | R2 保存・Class A | ○ 1 ファイルごと | ○（やり直し無し） | ― |
| 控え（`backup_d1.py backup`） | R2 保存・Class A・Class B、D1 読み出し | ○ 保存と Class A を見る | ○ PUT の前に数える | **直した**: 入れ物の確かめ（作る・lifecycle の PUT・GET）を数えていなかった |
| 戻す予行（`backup_d1.py drill`、restore-drill.yml） | Actions、D1 書き込み（新しい D1）、R2 Class B | ✕ だった | ― | **直した**: 書き込みの見込み（行 ×（1＋索引の数））が 1 万行を越えたら D1 に入れず手元で確かめる。Actions は plan `--mode drill` を通す（雛形） |
| 再生（`replay_job.py`、replay.yml） | Actions、D1 読み出し | ○ plan `--mode replay`・30 万行まで | ― | ― |
| Diagnose（taguri-crawler の diagnose.yml） | Actions | ✕ 手動 10 分 | ― | 残した（手動だけ） |
| 管理画面（`tools/admin`） | D1 書き込み・R2 保存・Class A | △ **別の控え**（`data/admin/free_tier/usage.json`）で、取得の使った量は見えない | ○ 送る前に数える | **直した**: 管理画面の R2 の保存に 0.5 GB の上限（`admin_r2_bytes`）。取得の 8 GB と足して 8.5 GB |
| Worker のポスター・名前の索引 | R2 Class B | ○ `r2ReadAllowed`（D1 の `usage`、20 回に 1 回 20 足す。数えられなければ読まない） | ― | ― |
| Worker の画面の書き込み | D1 書き込み・保存 | △ 保存は 4 GB で止める。1 日の書き込みの全体の上限は無い（1 人ずつの行の上限・修正依頼の上限・新規登録の上限はある） | ― | 残した |
| 定期実行: 空のアカウントの片付け（cleanup.js、10-18 追加） | D1 読み書き | △ 共通の数えは見ないが、1 回 50 人まで | ― | ― |
| 定期実行: 修正依頼の片付け（purgeFixRequests、10-18 追加） | D1 書き込み | ✕ 上限が無かった | ― | **直した**: 本文・行それぞれ 1 回 500 件まで（`FIX_PURGE_PER_RUN`） |
| 回数制限の様子（`/api/health` の rate_limit、10-18 追加） | なし | ― | ― | isolate の中で数えるだけ。D1 を使わない |
| Firebase の削除の保留（`fbdel:` の行、10-18 追加） | D1 書き込み | △ アカウントの削除 1 回に 2 文。アカウントの数（300）で抑えられる | ― | ― |
| 修正依頼のメール | Gmail | ○ 送る前に `usage` に数える（1 日 30 通） | ○ | ― |

## 4. 境目・競合・数えられないとき

| 場面 | どうなるか | 確かめ |
|---|---|---|
| 日の境目（D1） | 控えは UTC の日で数え、D1 も 0 時（UTC）に戻る。取得は 19:17 UTC（日本時間 4:17）なので、利用者の昼の操作が同じ UTC の日に先に入る | `test_d1_writes_are_counted_per_utc_day` |
| 月の境目（R2・Actions） | R2 の控えは UTC の暦の月。請求の月の区切りがずれても、上限が無料枠の 3 割なので越えない。Actions はどの 31 日の区切りでも 1,500 分に収まるかを見る | `test_every_31_day_window_stays_under_the_cap` |
| 予行と取得が同じ日 | 予行（毎月 3 日 03:41 UTC）と取得（19:17 UTC）は同じ UTC の日。予行は 1 万行までに抑えた | `test_a_drill_too_big_for_the_d1_day_is_checked_locally_and_not_loaded` |
| 複数のジョブ | Catalog どうしは `concurrency: catalog` で順番。Replay・予行は控えを書き戻さない。管理画面は別の控え | 読み合わせ |
| 失敗とやり直し | 送る前に数えるので、失敗した分も数える。ポスターのやり直しは 1 回ごとに上限を見る | `test_retries_stop_at_the_class_a_cap`、`test_r2_class_a_cap_counts_failed_puts` |
| Actions の分数が読めない | 毎日の更新だけ（45 分まで）。索引だけ・再生・予行は動かさない | `test_unknown_usage_reads_no_past_stages`、`test_restore_drill_runs_only_with_its_20_minutes_left` |
| Worker の R2 の数えが読めない | R2 を読まない（ポスターは Render の橋渡しから） | コード（`r2ReadAllowed` の catch）。上限で止まるのは `posters.test.js` |
| D1 の大きさが読めない | 書き込みを通す（D1 は請求しないので、止めるよりサービスを残す） | コード（`d1RoomLeft`）。上限で止まるのは `free-tier-d1.test.js` |
| **state ブランチを取り出せない** | **前は初回として続け、空の控えで R2 に入れ、最後に空の控えで state を上書きしていた**（R2 にある分を数えないので、請求の恐れ）。雛形を直し、ブランチがあるのに取り出せない・有無が分からないときは止める | 雛形 `catalog.yml` の「Restore the previous working data」 |

## 5. 直したもの（この点検で）

| 何を | どこ | 試験 |
|---|---|---|
| 修正依頼の片付けに 1 回 500 件の上限 | `cloudflare/src/free-tier.js`（`FIX_PURGE_PER_RUN`）・`src/screens/fixrequest.js` | `test/fixrequest.test.js` |
| ポスターのやり直しの 1 回ごとに Class A の上限を見る | `cloudflare/scripts/deliver_posters.py` | `test_retries_stop_at_the_class_a_cap` |
| 控えの入れ物の確かめ（Class A 2・Class B 1）を数え、上限の手前なら作らない | `cloudflare/scripts/backup_d1.py` | `test_backup_is_not_made_when_the_bucket_check_would_pass_the_class_a_cap` ほか |
| 予行の D1 の書き込みに 1 万行の上限（越えたら手元の SQLite で確かめるだけ） | `CAPS["drill_d1_writes"]`・`backup_d1.py drill` | `test_drill_writes_count_rows_and_their_indexes` ほか |
| 予行も Actions の plan を通す | `free_tier.py plan --mode drill`・雛形 `restore-drill.yml` | `test_restore_drill_runs_only_with_its_20_minutes_left` |
| 管理画面の R2 の保存に 0.5 GB の上限 | `CAPS["admin_r2_bytes"]`・`tools/admin/admin.py` | `test_the_admin_r2_storage_cap_stops_before_putting`・`test_separate_caps_keep_the_sum_under_the_free_tier` |
| state を取り出せないときは止める | 雛形 `tools/taguri/deploy/github-actions/catalog.yml` | （読み合わせ） |

**雛形の 2 つ（catalog.yml・restore-drill.yml）は、本番（非公開の taguri-crawler）に写すまで効かない。** README の約束どおり、同じ日に写して `diff` が空になることを確かめる〔q-crawler-template-sync-1018〕。

上限を緩めたものは無い。新しい上限を 3 つ足した（`admin_r2_bytes`・`drill_d1_writes`・`FIX_PURGE_PER_RUN`）。

## 6. 残したもの（大きい変更なので、案だけ）

| 何が足りないか | 案 | 記録 |
|---|---|---|
| 控え（台帳）と Cloudflare の観測の突き合わせが無い。控えが壊れる・消えると R2 を少なく数える | Free-tier check で Cloudflare の GraphQL Analytics（R2 の保存と操作の数）を読み、控えと大きい方で点検する（鍵に Analytics の読み取り権限が要る） | 〔q-r2-ledger-reconcile〕 |
| D1 の読み出しを数えていない | Worker で `meta.rows_read` を間引いて `usage` に足し、`/api/health` に出す | 〔q-d1-reads-real〕 |
| Worker の D1 の書き込みに全体の上限が無い | 同じく `meta.rows_written` を間引いて数え、1 日の利用者の分（約 1.5 万行）の 8 割で、増やす書き込みを止める | 〔q-d1-user-writes-uncapped〕 |
| 取得は D1 の大きさを見ずに書く | `deliver_*` の前に `wrangler d1 info` の大きさを読み、`D1_BYTES_CAP` を越えていれば入れない | 〔q-d1-user-writes-uncapped〕 |
| Workers の要求・Workers Builds の分を数えていない | どちらも越えると止まる（請求は無い見込み）。Builds は起案者がダッシュボードで月の分を見る | 〔q-workers-builds-minutes〕 |
| 管理画面と取得の控えが別 | 管理画面が state ブランチの控えを読む（書き戻しは取り合いになるので、読むだけ） | この文書の 3 |
| Diagnose は plan を通らない | 手動 10 分なので残す。増やすなら plan を足す | ― |

## 7. 確かめた試験（ローカル、2026-10-18）

- `cd cloudflare && node --test --experimental-test-isolation=none test/*.test.js` → 311 件すべて通過
- `cd cloudflare && python3 -m unittest discover -s test -p 'test_*.py'` → 全件通過
- 本番・隔離環境では動かしていない。本番の数字は Catalog #12 のログ（上の 1）だけ
