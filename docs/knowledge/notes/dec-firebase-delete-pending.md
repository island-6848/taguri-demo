---
id: dec-firebase-delete-pending
type: decision
status: proposed
date: 2026-10-18
title: 結び付いたアカウントを消すときは、Firebase UID のハッシュだけを 30 日残し、その間に同じ Google・メールでログインしたら、セッションを作らずにブラウザーに Google 側を消し直させる
sources:
  - https://github.com/island-6848/taguri-demo/issues/128
  - cloudflare/src/worker.js
  - cloudflare/src/client/login.js
  - cloudflare/public/privacy.html
  - cloudflare/test/firebase-auth.test.js
  - cloudflare/test/account-delete.test.js
links:
  - affects: dec-account-deletion
  - affects: q-firebase-user-deletion
  - depends_on: dec-firebase-auth
---
分かったこと（コードで確認、2026-10-18）: アカウントの削除は D1 を先に消し、Google 側（Firebase Authentication）の利用者はブラウザーが `deleteUser` で消す。失敗・離脱してもサーバーには何も残らず、失敗の文は「もう一度このページからログインして削除」と案内していたが、D1 の firebase_uid が消えているので、ふつうのログインは「未登録」で断られていた（issue #128）。

決めたこと（実装済み・保持の長さは起案者に確かめたいので proposed）:
- 結び付いたアカウントを消す batch に、`usage` の 1 行を足す: キーは `fbdel:` + SHA-256（Firebase UID）、値は期限（いま + 30 日）。UID そのもの・メールは残さない。期限の過ぎた行は、次に書くときに消す。migration は使わない
- 返事は `{deleted, firebase_linked: true, firebase_pending: true}`。サーバーは Google 側を消し終えたとは言わない
- 期限の内に同じ Google・メールでログインすると（ログイン・新規登録のどちらの欄からでも、結び付けを除く）、`/api/auth/firebase` はセッションもアカウントも作らずに `{firebase_delete_pending: true}` を返す。ブラウザーはいまログインしたばかりなので `deleteUser` で消し直せる。消せなければ、またログインすればやり直せる
- ブラウザーの「消せた」という申告では行を消さない（確かめられないので、30 日で消えるまで残す）。消せていれば Firebase は次から別の UID を出すので、残った行は誰にも当たらない
- privacy.html の 6 に、ハッシュ値を 30 日残すことを書き足した
- 無料枠: 結び付いたアカウントの削除 1 回につき usage に 1 行（最大でも 300 人分）、ログインのときに 1 行読むだけ

分からないこと・残り:
- 30 日でよいか（記録の無いアカウントを消す 1 か月〔cleanup.js〕に合わせた）。短いほど残る情報は少ないが、やり直せる期間も短くなる
- 記録の無いアカウントの自動削除（cleanup.js の sweepEmptyAccounts）は、この保留を書かない（その人が戻ってきたときに、Google 側を勝手に消さないため。privacy.html の 6 のとおり、Google 側は残る）
- Google 側が本当に消えたかは、サーバーからは確かめていない（Firebase の管理 API を使わない）。q-firebase-user-deletion は open のまま
