---
id: dec-session-one-week
type: decision
status: adopted
date: 2026-10-19
title: セッションは既発行分を含めログインから1週間で失効する
sources:
  - cloudflare/src/session-policy.js
  - cloudflare/src/worker.js
  - cloudflare/src/screens/account.js
  - cloudflare/test/firebase-auth.test.js
links:
  - affects: comp-firebase-login
---
起案者の指定「発行済みセッションの期限１週間にしたい」。新規CookieのMax-AgeとDB有効期限を604800秒にそろえる。既発行の30日Cookieも、サーバーがcreated_atを検証し、発行から7日ちょうどで拒否する。created_atの無いセッションも再ログインが必要。読み取りで延長しない。

ページの認証ゲート、API、Firebaseの既存アカウント結び付け、アカウントのログイン端末数に同じ上限を適用する。ログイン時の片付けでも7日を超えたセッションを削除する。Firebase側の失効との同期を追加する変更ではない。

新しい外部問い合わせ・テーブル・保存行は増やさず、既存SELECTの条件を追加するだけ。DBの移行や一括書き込みを必要としない。新規Cookie・DBの7日間、旧Cookieの期限境界、期限後のAPI拒否・ページ転送・結び付け拒否を既存の統合テストへ追加。
