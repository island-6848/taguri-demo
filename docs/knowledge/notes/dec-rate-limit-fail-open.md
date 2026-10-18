---
id: dec-rate-limit-fail-open
type: decision
status: proposed
date: 2026-10-18
title: 回数制限が無い・壊れたときも要求は通す（認証口も）。代わりに /api/health の rate_limit に出し、1 時間ごとの見張りで持ち主に知らせる
sources:
  - https://github.com/island-6848/taguri-demo/issues/133
  - cloudflare/src/rate-limit.js
  - cloudflare/src/worker.js
  - cloudflare/test/rate-limit.test.js
  - tools/taguri/check_service.py
  - tools/taguri/test_check_service.py
links:
  - depends_on: dec-rate-limit
  - affects: comp-auth-throttle
---
issue #133。`allowed` は、Rate Limiting の結び付けが無いときも、`limit()` が例外を投げたときも true を返す。それ自体は〔dec-rate-limit〕のとおり（無料枠を守るための制限で、サービスを止めるためのものではない）。ただ、止まっても外から分からなかった。

## したこと
- `/api/health` に `rate_limit: {any, auth}` を足した。それぞれ `state`（`missing`＝結び付けが無い・`failing`＝この 10 分に失敗した・`ok`）と、`checked`・`limited`（正常に 429 にした数）・`errors` の数。数は Worker の isolate の中だけで、D1 には書かない（使う量は増えない）。接続元の住所や鍵は出さない。
- 失敗したときのログは、種類ごとに 1 分に 1 行（`rate limit auth: binding failed (TypeError)`）。結び付けが無いときは isolate ごとに 1 行。住所・鍵・エラーの本文は出さない。
- `check_service.py`（`service-watch.yml`、1 時間ごと）が `missing`・`failing` を問題として数え、失敗にする。GitHub から持ち主にメールが届く。足したのは JSON を見るだけなので、Actions の分は増えない（公開リポジトリなので無料でもある）。
- 試験：結び付け無し・例外・正常な 429 を health で区別できること、失敗のログが 1 分に 1 行で住所を含まないこと、10 分で ok に戻ること。

## 障害時の方針（起案者に確かめてほしいので proposed）
認証口（新規登録・復旧コード・Firebase・パスキー）も、制限が外れたときは通す。止めると、結び付けの故障でログインもできなくなるため。外れても当て推量で入れないことは別に守られている:
- 復旧コードは 256 ビットの乱数。Firebase の ID トークンは署名を確かめる。パスキーは本人確認つき。
- 新規登録は D1 の正確な上限（1 日 30 人・接続元ごとに 1 日 3 件・全体 300 人）がある。
- パスキーの未処理チャレンジは接続元ごとに 10 件まで（issue #73）。
D1 で数える代わりの制限は足していない（要求ごとに D1 に書くことになり、無料枠の書き込みを使うため）。

## 分かっていないこと
- 状態は isolate ごとなので、見張りが当たった isolate が失敗を見ていなければ `ok` と出る。health は 5 分控えられる（Cache-Control）。結び付けが無いこと（`missing`）は、どの isolate でも同じに出る。
- 本番の結び付けの様子はまだ見ていない。デプロイの後に `/api/health` の `rate_limit` が両方 `ok` か、次の見張りの実行（または手動の Service watch）で確かめる。
