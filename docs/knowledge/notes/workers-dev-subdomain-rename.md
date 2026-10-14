---
id: workers-dev-subdomain-rename
type: finding
status: confirmed
date: 2026-10-14
title: workers.dev の URL は無料のまま名前を変えられる（アカウントの subdomain と Worker の名前）。独自ドメインは年額がかかる
sources:
  - https://developers.cloudflare.com/workers/configuration/routing/workers-dev/
  - https://alchemy.run/providers/cloudflare/workers/subdomain
  - https://domainoffer.net/tld/com/cloudflare
links:
  - affects: q-domain
  - supports: dec-free-tier-only
---
公式の説明（検索結果の引用で確かめた）: Workers & Pages の画面で「Your subdomain」の Change を押すと、アカウントの workers.dev の名前を変えられる。Worker の URL は「<Worker の名前>.<アカウントの名前>.workers.dev」。名前の変更は無料。二次情報（alchemy.run）: subdomain は全アカウントで重複できず、1 アカウント 1 つ。変えると workers.dev で動く全 Worker の URL が変わる。公式は本番には独自ドメインか route を勧めている。
独自ドメイン（taguri.com など）は登録に年額がかかる: Cloudflare Registrar の .com は年 10.46 ドル前後（集計サイト domainoffer.net、unverified な数字。以前の記録 com-wholesale-2026 は年 11 ドル強）。taguri.com が空いているかは、この作業環境から登録の記録（RDAP）を引けず、確かめられなかった。
