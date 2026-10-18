---
id: dec-login-email-ttl
type: decision
status: proposed
date: 2026-10-18
title: メールのリンクでのログインのために端末に控えるアドレス・どちらの欄か・同意の版は、1 時間で消す（Google・パスキーを始めたとき・ログアウトしたときも消す）
sources:
  - https://github.com/island-6848/taguri-demo/issues/132
  - cloudflare/src/client/login-store.js
  - cloudflare/src/client/login.js
  - web/app.js
  - cloudflare/test/login-store.test.js
  - docs/cloudflare-security-review.md
links:
  - affects: q-login-email-storage
  - affects: comp-firebase-login
---
分かったこと（コードで確認、2026-10-18）: メールのリンクを送ると、アドレス・登録かログインか・同意の版を localStorage に置き、リンクを開いて処理したときだけ消していた。メールを開かずに離れると、期限なしで残った（issue #132、点検の S9）。

決めたこと（実装済み・長さは起案者に確かめたいので proposed）:
- 控えた時刻（`taguri_login_saved_at`）も置き、`/login` を開くたびに、1 時間を過ぎた控え・時刻の無い古い控え・時刻が先の日付になっている控えを消す（`login-store.js` の `expire`）。点検の S9 の案と同じ 1 時間
- 消す場面: リンクで戻って処理したとき（前から）・Google やパスキーでのログイン・登録を始めたとき・アカウントのページでログアウトしたとき（web/app.js。この端末・すべての端末のどちらでも）・期限切れ
- 期限が切れたあとにリンクを開いたとき: アドレスを入力し直せば、ログインの欄として続けられる（どちらの欄かが消えると 'login' の扱いになり、アカウントを作らない）。新規登録だったときは、同意の版も消えているので、サーバーが「新規登録から」と断る。送り直せば続けられる。どちらも安全な側に倒れる
- 送ったときの文に「1時間以内に」を足した
- サーバー・D1 の使う量は変わらない（ブラウザーの中だけ）

分からないこと: Firebase のメールのリンクそのものの有効期間は、公式の文書では確かめていない（リンクの方が長くても、上のとおりアドレスを入れ直せば続けられる）。q-login-email-storage（アドレスを端末に置いてよいか）は、起案者の判断なので open のまま。
