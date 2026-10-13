# 無料枠の約束と上限の一覧

> **たぐりは有料のものを 1 つも使わない。無料枠を越えそうなら、使う前に止めて知らせる。**
> 起案者の指示（2026-10-13）「必ず無料の範囲内にして。絶対超えないで。つねに警戒してチェックして。
> 全資料に書き込んで、厳重に管理して。」〔dec-free-tier-only〕
>
> この方針を変えられるのは起案者だけ。有料プランへの切り替え・支払いの上限の引き上げ・独自ドメインの購入は、
> 起案者がはっきり指示しない限りしない。勧めることもしない（無料のまま使う量を減らす案を出す）。

上限の数字は、取得の側は `cloudflare/scripts/free_tier.py` の `CAPS`、Worker の側は
`cloudflare/src/free-tier.js` の `R2_READS_CAP` にだけ書く。変えるときは、この表とナレッジグラフも直す。

## 使っているものと上限

| サービス | 無料枠 | 越えたとき | たぐりの上限 | 守り方 |
|---|---|---|---|---|
| **Cloudflare R2**（ポスター） | 保存 10 GB-月・Class A 月 100 万回・Class B 月 1,000 万回〔r2-free-tier-billed〕 | **請求される** | 保存 8 GB・Class A 月 30 万回・Class B 月 300 万回 | 入れる前に控えで数える（`deliver_posters.py`）。読み出しは Worker が D1 の `usage` 表に数え、上限で R2 を読むのをやめる（`free-tier.js`）。数えられないときも読まない |
| **GitHub Actions**（非公開の taguri-crawler） | 月 2,000 分（アカウント全体）〔gha-private-free-minutes〕〔gha-minutes-reset-budget〕 | 止まる（起案者の GitHub には支払い方法が無いので請求されない〔q-free-tier-account-settings〕）。月末まで取得が止まる | 直近 31 日で 1,500 分 | ジョブの最初の段（`free_tier.py plan`）が API で分数を数え、これからの 31 日のどの区切りでも収まるときだけ動かす。過去の公演を読む分数もここで決める |
| GitHub Actions（公開の taguri-demo） | 標準の実行環境は無料〔github-actions-public-free〕 | ― | ― | 非公開の作業はここで動かさない（ログが公開されるため） |
| **Cloudflare D1** | 1 日 読み 500 万行・書き 10 万行、保存 5 GB〔d1-free-limits〕 | その日はエラー（請求なし） | 取得の書き込み 1 日 8 万行（残りは利用者の操作） | 書く前に控え（`data/free_tier/usage.json`）に足す。公演一覧 6 万行・過去の公演 2 万行・ポスター 4,000 行の各上限もある |
| **Cloudflare Workers** | 1 日 10 万要求・1 回 CPU 10 ミリ秒〔workers-free-cpu-10ms〕 | 止まる（請求なし） | ― | 静的ファイルは数えない〔workers-static-assets-free〕。ポスターはブラウザに 1 週間置く（`immutable`） |
| Workers Builds（自動配信） | 月 3,000 分〔workers-builds-free-3000〕 | 止まる見込み（未確認） | ― | 1 回 1〜2 分 |
| Render（デモ・橋渡し先） | 月 750 時間〔render-free-spin-down〕 | 月末まで止まる | ― | 無料プランのまま |
| GitHub Pages（デモ） | 無料 | ― | ― | ― |
| Firebase Authentication | 無料の Spark プラン〔q-firebase-free-tier〕 | ― | ― | カード登録をしない |
| Gemini API | 使う場合も月の呼び出しに上限〔gemini-budget-cap〕 | ― | 月 300 回（既定） | 取得では呼ばない |

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
