# 無料枠の約束と上限の一覧

> **たぐりは有料のものを 1 つも使わない。無料枠を越えそうなら、使う前に止めて知らせる。**
> 起案者の指示（2026-10-13）「必ず無料の範囲内にして。絶対超えないで。つねに警戒してチェックして。
> 全資料に書き込んで、厳重に管理して。」〔dec-free-tier-only〕
>
> この方針を変えられるのは起案者だけ。有料プランへの切り替え・支払いの上限の引き上げ・独自ドメインの購入は、
> 起案者がはっきり指示しない限りしない。勧めることもしない（無料のまま使う量を減らす案を出す）。

## 例外: アプリの配信（起案者が負担する）

起案者の指示（2026-10-20）「本格的に配信リリースするときの経費は負担する。アプリにしたい。」〔dec-app-release-costs〕

- 例外は **ストアに出すための登録料だけ**: Apple Developer Program（年 99 米ドル）・Google Play Console（登録時に 1 回 25 米ドル）〔f-app-store-fees〕。払うのは起案者で、たぐりのコードや定期実行が払うものは無い
- サーバー・保存・定期実行・通知の送信は **今までどおり無料枠の中だけ**。上の表と上限はそのまま
- それ以外の有料のもの（独自ドメイン・有料のビルドサービス・有料プラン・従量課金の API など）は、今までどおり起案者がはっきり指示するまで使わない・勧めない

上限の数字は、取得・管理画面・控えの側は `cloudflare/scripts/free_tier.py` の `CAPS`、Worker の側は
`cloudflare/src/free-tier.js`（`R2_READS_CAP`・`D1_BYTES_CAP`・`MAX_ACCOUNTS`・`FIX_*` など）にだけ書く。変えるときは、この表とナレッジグラフも直す。
使う側を全部足した点検は `docs/free-tier-audit-2026-10-18.md`（issue #139）〔free-tier-audit-1018〕。

## 使っているものと上限

| サービス | 無料枠 | 越えたとき | たぐりの上限 | 守り方 |
|---|---|---|---|---|
| **Cloudflare R2**（ポスター） | 保存 10 GB-月・Class A 月 100 万回・Class B 月 1,000 万回〔r2-free-tier-billed〕 | **請求される** | 保存 8 GB・Class A 月 30 万回・Class B 月 300 万回 | 入れる前に控えで数える（`deliver_posters.py`）。読み出しは Worker が D1 の `usage` 表に数え、上限で R2 を読むのをやめる（`free-tier.js`）。数えられないときも読まない |
| **GitHub Actions**（非公開の taguri-crawler） | 月 2,000 分（アカウント全体）〔gha-private-free-minutes〕〔gha-minutes-reset-budget〕 | 止まる（起案者の GitHub には支払い方法が無いので請求されない〔q-free-tier-account-settings〕）。月末まで取得が止まる | 直近 31 日で 1,600 分（一時的。2026-10-20 に 1,500 から上げた〔dec-past-2026-first〕） | ジョブの最初の段（`free_tier.py plan`）が API で分数を数え、これからの 31 日のどの区切りでも収まるときだけ動かす。過去の公演を読む分数もここで決める。推薦の索引だけを入れる手動実行（mode `index`、数分）も同じ点検を通し、分数が読めないときは動かさない〔dec-index-only-run〕。推薦の再生（Replay）と控えから戻す予行（Restore drill、月 1 回）も 20 分が残るときだけ動かす（`--mode replay`・`--mode drill`）。手動の Diagnose（10 分）だけは点検を通らない。**優先順位（2026-10-21〔dec-crawl-tiers〕）:** 毎日の更新（新しい公演の発見・これからの公演・変更の確認、見積もり 15 分）の分を先に取っておき、過去の公演・ポスター・再生・予行・本文は、その残りから余白 30 分を引いた分だけを使う。下位の段にはすべて時間の上限があり、続きは次回。点検の段は、この実行の段ごとの時間を控え（`usage.json` の `runs`）、毎日の更新の実測を Summary に出す |
| **D1 の読み出し**（Worker と取得の合計） | 1 日 500 万行〔d1-free-limits〕 | 止まる（2026-10-20 に越えた〔d1-reads-over-1020〕） | 直近 24 時間で 300 万行で知らせる（`CAPS["d1_reads_day"]`） | 取得の点検の段が `wrangler d1 info --json` の `rows_read_24h` を表に出す（鍵に分析を読む権限が無ければ「読めなかった」）。取得の各段の rows_read もログから足して控える（`usage.json` の `d1_reads`）〔f-deliver-past-reads〕 |
| GitHub Actions（公開の taguri-demo） | 標準の実行環境は無料〔github-actions-public-free〕 | ― | ― | 非公開の作業はここで動かさない（ログが公開されるため） |
| **Cloudflare D1** | 1 日 読み 500 万行・書き 10 万行、保存 5 GB〔d1-free-limits〕 | その日はエラー（請求なし） | 取得の書き込み 1 日 8 万行（残りは利用者の操作） | 書く前に控え（`data/free_tier/usage.json`）に足す。公演一覧 6 万行・過去の公演 2 万行・ポスター 4,000 行の各上限もある。おすすめのカード（rec_card）は 1 日に「これからの公演の数 × 2 行」で、予算の残りを越える日は入れない〔dec-recommend-worker-cards〕。索引だけの手動実行も同じ控えから残りを引くので、同じ日に何回動かしても 8 万行を越えない〔dec-index-only-run〕。眺めるの「比べる」の相手は 1 日 1 回だけ数え、rec_meta に 1 行書いて使い回す〔dec-records-worker〕。推薦を測るための記録（rec_shown）は、1 人 1 日 1 画面 1 行で、書き直しは 1 日 6 回まで（300 人で最大 3,600 行）。答えの行の順位・点は同じ行に入れるので増えない〔impl-eval-logging〕。劇場制覇マップの分母（venue_census、約 1,360 行）は、変わった行だけ 1 行 2 書き込みで送り、県ごとの数は rec_meta の 1 行。初回は約 2,720 書き込みで、その日の残りに全部が収まらなければ次の日に回す〔impl-theater-conquest〕。画面は本人が行った会場の分だけ引く。控えから戻す予行が新しい D1 に書く分も口座の 1 日 10 万行に入るので、1 万行（`CAPS` の `drill_d1_writes`）を越える控えは D1 に入れず手元で確かめる〔dec-free-tier-audit-fixes-1018〕。**保存は D1 自身が返す大きさ（meta.size_after）で見て、4 GB（8 割）で書き込みと新規登録を止める（外す・消す操作とログアウト・アカウントの削除は通す〔dec-cap-allows-shrinking〕）。利用者は 300 人まで・新規は 1 日 30 人まで**（数えた根拠は〔dec-account-cap-counted〕）。過去の公演の題名の読み直し（冠名・サブタイトル）は、配送の同じ 1 日の枠の中で 1 行 2 書き込みの UPDATE。読み直しの取得は過去の公演の分数の 3 割で、分数は増えない〔dec-past-title-backfill〕。作品ごとに分けた評価（work_piece）は 1 記録 20 作品・1 人 2,000 行までをトリガーで守る。保存 1 回は 6 作品で約 25 行の書き込み、読みは本人の行だけ〔dec-split-pieces〕 |
| **Cloudflare Workers** | 1 日 10 万要求・1 回 CPU 10 ミリ秒〔workers-free-cpu-10ms〕 | 止まる（請求なし） | ― | 静的ファイルは数えない〔workers-static-assets-free〕。眺めるの重い 2 枚（人の流れ・相関図）は 10 ミリ秒を越えるので、Worker では組まずにブラウザで組む（/figs/ の静的ファイル）〔dec-records-worker〕。ポスターはブラウザに 1 週間置く（`immutable`） |
| Workers Builds（自動配信） | 月 3,000 分〔workers-builds-free-3000〕 | 止まる見込み（未確認） | ―（数えていない） | 1 回 1〜2 分。2026-10 は master に 1 日 約 19 回押していて月 約 570〜1,180 分。1 日 50 回を越えて押すと越えうる〔q-workers-builds-minutes〕 |
| D1 の控え（`backup_d1.py`、R2 の入れ物 taguri-backup） | R2 の枠の中（入れ物を分けても口座で合計） | **請求される**（R2） | 取得の控えと同じ R2 の上限 | 控えの PUT と入れ物の確かめ（作る・lifecycle の PUT・GET）を送る前に数える。30 日分だけ置く |
| Render（デモ・橋渡し先） | 月 750 時間〔render-free-spin-down〕 | 月末まで止まる | ― | 無料プランのまま |
| GitHub Pages（デモ） | 無料 | ― | ― | ― |
| X の埋め込み用の口（oEmbed、publish.twitter.com。感想に貼ったポストの本文を読む） | 無料・鍵なし・回数の上限なし〔dec-x-post-note〕 | ― | ― | X の API（2026-02 から読むたびに有料）は使わない。貼られた URL 1 つにつき 1 回だけ読み、D1 は読まない（ログインの確かめだけ） |
| Anthropic の Claude API（同意した人の感想の読み取り、Claude Haiku 5.5） | Max 5x の毎月 100 ドルの API の枠（起案者のプラン。Console に支払い方法を登録しない）〔dec-note-ai〕 | 枠を使い切った月は API が止まる（請求なし。支払い方法を登録していないため） | 1 か月の入出力 500 万トークン（`note-ai.js` の `NOTE_AI_TOKENS_CAP`、Haiku 5.5 で約 0.6 ドル） | 夜の定期実行だけで送る（1 晩 10 回・200 件まで）。同じ感想は 1 度だけ。使った量を D1 の `usage` に数え、上限の月は送らない。Console の支払い方法と自動の補充（auto-reload）は付けない |
| Firebase Authentication | 無料の Spark プラン〔q-firebase-free-tier〕 | ― | ― | カード登録をしない |
| あらすじの読み取り（運営者の Claude の定期実行） | 有料の API は使わない | ― | 1 回 60 件・1 日 4 回まで〔q-synopsis-routine-quota〕 | 取得では LLM を呼ばない〔dec-synopsis-reader-claude〕 |
| Gmail（公演修正依頼の知らせ） | 個人の Gmail は 1 日 500 通まで〔fix-request-mail〕 | その日は送れない（請求なし） | 1 日 30 通（`free-tier.js` の `FIX_MAILS_PER_DAY`）・依頼は 1 人 1 日 5 件 | Worker が送る前に D1 の `usage` に数える。越えた日は保存だけして管理画面で見る〔impl-fix-request〕。保存は 1 人の未対応 10 件・1 人 50 件・全体 2,000 件（約 6 MB）までで、INSERT の条件で守る。対応済みは 30 日で本文、180 日で行を消す（定期実行で 1 日 2 文、それぞれ 1 回 500 件まで `FIX_PURGE_PER_RUN`）〔dec-fix-request-retention〕〔dec-free-tier-audit-fixes-1018〕 |
| 管理画面（手元・`tools/admin`） | 上の D1・R2 の枠の中 | ― | D1 の書き込み 1 日 1,000 行・ポスター月 300 枚・R2 の保存 0.5 GB（`CAPS` の `admin_*`） | 書く前に控え（`data/admin/free_tier/usage.json`）で数える。この控えは取得の控えと別のファイルで、取得が使った量は見えないので、管理画面の分だけの上限で止め、取得の上限と足しても無料枠に収める（R2 の保存は 8 GB ＋ 0.5 GB）〔free-tier-audit-1018〕。読み取り（あらすじ → 題材）は手元の Claude Code で、従量課金の API キーは渡さない〔impl-admin-tool〕 |

R2 だけは **越えると止まらずに請求される**。Cloudflare には使いすぎを止める仕組みが無く、
予算の通知（Budget alerts）は知らせるだけ〔cf-budget-alerts-not-cap〕。だからコードの上限を守りの本体にする。

## 見張り

- **毎日:** Catalog のジョブの最後の段（Free-tier check、`free_tier.py check`）が、使った量と上限の表を
  実行の Summary に出す。どれかが **上限の 8 割** を越えたか、数えられなかったら失敗する。失敗すると GitHub から持ち主に通知が届く
- **いつでも:** Worker の公開の `/api/health` が、今月の R2 の読み出しの数と上限を返す（数だけ。利用者のことは出さない）
- **最後の歯止め（起案者の設定）:** GitHub には支払い方法を登録しない（登録しなければ使い切った時点で止まり、請求されない）。Cloudflare は R2 のために支払い方法を登録したので、Budget alerts 0.01 ドルを作る
  〔q-free-tier-account-settings〕

## 作業するときの約束

- 新しく外のサービスや機能を使う前に、無料枠と「越えたら止まるか、請求されるか」を公式の料金表で確かめ、この表とナレッジグラフに書く
- 請求されうるもの（今は R2）は、必ずコードで上限の手前で止める。止める仕組みの試験を書く
- 使う量が増える変更（取得の枚数・定期実行の回数・保存するもの）は、この表の上限に収まるかを数えてから入れる
- 上限に近づいたら、有料にせず、使う量を減らす（新規登録を止める `ALLOW_REGISTRATION=false`、取得を減らす、古いポスターを消す〔q-r2-poster-growth〕）
