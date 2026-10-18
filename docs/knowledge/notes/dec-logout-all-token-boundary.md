---
id: dec-logout-all-token-boundary
type: decision
status: proposed
date: 2026-10-18
title: 「すべての端末でログアウト」は、全セッションを消し、その時刻より前のログインで得た Firebase の ID トークンも受け付けなくする（users.tokens_valid_after、migration 0033）
sources:
  - https://github.com/island-6848/taguri-demo/issues/127
  - cloudflare/migrations/0033.sql
  - cloudflare/src/worker.js
  - cloudflare/src/firebase-auth.js
  - cloudflare/test/firebase-auth.test.js
links:
  - depends_on: dec-firebase-auth
  - affects: comp-firebase-login
---
分かったこと（コードで確認、2026-10-18）: 全端末のログアウトは sessions を消すだけだった。署名・期限が有効で auth_time が 5 分以内（`MAX_AUTH_AGE`）の ID トークンを持つ人は、ログアウトの直後でも `/api/auth/firebase` で新しいセッションに換えられた（issue #127）。

決めたこと（実装済み・範囲は起案者に確かめたいので proposed）:
- 「すべての端末」の範囲 = (1) そのアカウントのすべてのセッション（Cookie）と、(2) その時刻（秒）以前に Google・メールでした本人確認（ID トークンの auth_time）
- `/api/logout/all` は 1 つの batch で `users.tokens_valid_after = いま` とし、セッションを消す。`firebaseSignIn` は、結び付いたアカウントのトークンの auth_time が tokens_valid_after 以下なら 401 にする。新しく Google・メールでログインし直せば（auth_time が新しくなる）入れる。同じ秒のものは拒む方に倒した
- Firebase の更新トークンで作り直した ID トークンも auth_time は元のままなので、同じく拒まれる
- パスキー・復旧コードのログインは、その場の本人確認なので境界を見ない（復旧コードが漏れたときは作り直す〔dec-recovery-reissue〕）
- 「この端末でログアウト」は境界を動かさない（その端末の Cookie を消すだけ）
- 列は users に 1 つ（アカウントの削除で一緒に消える）。書き込みは全端末のログアウト 1 回につき 1 行増えるだけで、読みはログインのときに同じ行を読むので増えない

分からないこと: Firebase 側（Google のアカウント・ブラウザーに残る Firebase のログイン）はサーバーから消さない。ほかの端末のブラウザーに残った Firebase のログインは、たぐりのセッションには換えられない（5 分を過ぎた auth_time は拒む）が、Firebase 側の記録としては残る。
