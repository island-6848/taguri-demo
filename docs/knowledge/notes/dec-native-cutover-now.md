---
id: dec-native-cutover-now
type: decision
status: adopted
date: 2026-10-14
title: 本番を全画面そろう前に Worker の画面へ切り替え、Render のデモへの中継をやめる（未移植の画面は「移しています」と出す）
sources:
  - cloudflare/src/worker.js
  - cloudflare/src/screens/index.js
  - cloudflare/src/screens/suggest.js
  - cloudflare/wrangler.jsonc
  - cloudflare/test/cutover.test.js
links:
  - answers: q-native-cutover
  - affects: comp-native-screens
  - affects: dec-render-full-migration
---
起案者の指摘（2026-10-14）「本番用のサイトなはずなのに、デモ用の内容がでる。最初ログイン（会員登録）したらデータは空なはず」。原因は、本番の Worker がまだ移していない画面を Render のデモ版（見本の 96 件を誰にでも見せる）へ中継していたこと（native-cutover-map）。
起案者に選んでもらった（AskUserQuestion）: 「今すぐ切り替え」（ほかの案は「全部移してから一度に」「移すまで本番を閉じる」）。計画書の「最後に一度だけ切り替える」（dec-render-full-migration）は、この点だけ取りやめる。
やったこと:
- wrangler.jsonc の vars に NATIVE_UI=all。移した画面（評価一覧・未評価・感想・日記帳）と書き込みは D1 から答える
- まだ移していない 13 画面（おすすめ・興味あり・お気に入り・公演カレンダー・開幕リマインド・購入済み・眺める・たどる・観劇史年表・探す・設定・はじめる・登録）は、Worker が「この画面は、いま新しい仕組みに移しています」と答える（movingScreen。応答に moving: true）。まだの書き込みは 503
- Render へ行くのは、R2 にまだ無いポスター（/img/）だけ。公演の候補（/api/suggest）は Render のものがデモの記録を「自分の記録」として混ぜるので、Worker で答える（screens/suggest.js。自分の works・rec_gram の今の公演・past_stage の題名の前方一致。Python と同じ形だが一字一句の一致はしない）
- public/config.js の版を service に（デモの断り書き・制限の文がサービス版の文になる）
- 古い「アカウント・記録」（/migration-data/）への入り口は出さない。代わりに新しいアカウントの画面〔dec-account-page〕
無料枠: 候補は 1 文字打つごとに D1 を読む。rec_gram は文字の組ごとに数行、past_stage は索引で 20 行まで、works は本人の分だけで、1 回あたり数十行。1 日 500 万行の枠に対して小さい。Workers の要求は増えない（同じ要求の答え先が変わるだけ）。
残り（q-native-cutover の 2〜6 はまだ）: おすすめから順に 13 画面を移す。/migration-data/ の records を works に移すか。Render をいつ止めるか。
