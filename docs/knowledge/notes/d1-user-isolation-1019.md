---
id: d1-user-isolation-1019
type: finding
status: confirmed
date: 2026-10-19
title: D1 は外から直接は読めず、Worker 経由でもログイン中の本人の記録しか返さない。全員分が見えるのは Cloudflare の管理画面（アカウントの持ち主）だけ
sources:
  - https://github.com/island-6848/taguri-demo/blob/master/cloudflare/wrangler.jsonc
  - https://github.com/island-6848/taguri-demo/blob/master/cloudflare/src/worker.js
  - https://github.com/island-6848/taguri-demo/tree/master/cloudflare/migrations
links:
  - affects: q-review-1015
---
起案者の問い「D1 は他のユーザーの全データも見えてしまう状態か」に、master のコードを読んで答えた（2026-10-19）。

- D1 は `wrangler.jsonc` の `d1_databases` で Worker に `DB` として結び付けているだけ。D1 に公開の URL は無く、読めるのは Worker と、Cloudflare アカウントにログインできる人（管理画面・wrangler）だけ
- ログインなしで開ける API は `/api/register`・`/api/recover`・`/api/catalogue`・`/api/health` だけ（`PUBLIC_APIS`）。どれも個人の記録は返さない（health は件数などの集計）
- 個人の表（records・favourites・reactions など）を読む SQL は `WHERE user_id=?` で、`uid` はセッションのクッキーから引く（`user()`）。画面から別の人の id を指定する口は見当たらなかった。user_id で絞らない SQL は件数の数え上げ、セッション（ハッシュで照合）、劇場と都道府県の対応のような共有の表だけ
- 保存しているのは、セッション・復旧コードともハッシュだけ。users にメールアドレスや名前の列は無い（firebase_uid は有る）
- Cloudflare の管理画面の D1 コンソールでは全員分の行が見える。これは持ち主としての閲覧で、他の利用者から見えるわけではない

分からなかったこと: 全部の画面（`src/screens/` の 50 余り）の SQL を 1 本ずつ確かめたわけではない（user_id 抜けを grep で拾っただけ）。Cloudflare アカウントに他の人を招いているか（招いた人は全員分を読める）はコードからは分からない。
