---
id: find-session-secret-overrides-env
type: finding
status: confirmed
date: 2026-10-24
title: クラウドのセッションでは、環境の「シークレット（Bearer）」の値が、環境変数のトークンより優先して付けられる。古いトークンを残すと、D1・R2 だけが Authentication error になる
sources:
  - https://code.claude.com/docs/en/cloud-environments#network-access
links:
  - depends_on: q-crawl-in-session
---
**起きたこと（2026-10-24、このセッションの実行結果）**
- 起案者が Cloudflare のトークンを作り直し（D1 Edit・Workers R2 Storage Edit・Account Analytics Read）、古いものを消した。環境変数 `CLOUDFLARE_API_TOKEN` は新しい値になったが、環境のシークレット（Bearer、`api.cloudflare.com`、パス `/client/v4/accounts/`）は古い値のままだった。
- 行き先で結果が分かれた:
  - `/client/v4/accounts/…`（D1・R2）: 古い値が付けられて `Authentication error (10000)`
  - `/client/v4/user/tokens/verify`・`/client/v4/graphql`: 環境変数の値がそのまま届いて成功（active。D1 の分析も読めた）
- シークレットを消すと、D1・R2 とも通った。シークレットの値は、リクエストに付いている Authorization ヘッダーを上書きする（ダミーの `Bearer via-proxy` でも通ったのと同じ仕組み）。

**決まり**
- トークンを作り直したら、GitHub の secrets（taguri-crawler）と、セッション環境の環境変数・シークレットを全部そろえる。どれかに古い値を残さない。
- wrangler は環境変数 `CLOUDFLARE_API_TOKEN` が空だと止まる（非対話の環境）。シークレットだけで動かすときは、環境変数にダミーの値を置く。

**その後**
- 止まっていた過去の公演のポスター 678 件を D1 の poster 表に入れた（rows_written 1,356）。state ブランチは 7617dbc。
