---
id: f-wrangler-d1-info-reads
type: finding
status: confirmed
date: 2026-10-21
title: wrangler d1 info <名前> --json は、D1 の分析（GraphQL の d1AnalyticsAdaptiveGroups）から直近 24 時間の rows_read_24h・rows_written_24h・read_queries_24h を返す
sources:
  - cloudflare/node_modules/wrangler/wrangler-dist/cli.js
links:
  - supports: dec-crawl-tiers
---
wrangler 4.151.1 の取り出したコード（cloudflare/node_modules/wrangler/wrangler-dist/cli.js の d1 info の handler）で確かめた。Cloudflare の公式の文書は、この環境から開けなかった（developers.cloudflare.com へつながらない）。
- 返す値: GraphQL の `viewer.accounts(filter: {accountTag}).d1AnalyticsAdaptiveGroups(limit: 10000, filter: {datetimeHour_geq: 24 時間前, datetimeHour_leq: 今, databaseId})` の `sum { readQueries writeQueries rowsRead rowsWritten }` を足した数を、`read_queries_24h`・`write_queries_24h`・`rows_read_24h`・`rows_written_24h` として JSON に入れる
- 分析が取れなかったとき（graphqlResult が無い）は、この 4 つの鍵が無い
- 分からないこと: 取得の鍵（CLOUDFLARE_API_TOKEN）に分析を読む権限があるか。無ければ点検の表は「読めなかった」になる（注意だけ）
