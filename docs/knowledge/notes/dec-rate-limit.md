---
id: dec-rate-limit
type: decision
status: adopted
date: 2026-10-14
title: 回数制限は Cloudflare の Rate Limiting binding（訪問者ごとのブレーキ）と、新規登録の 1 日の上限（D1 で正確に数える）の二段にする
sources:
  - cloudflare/src/rate-limit.js
  - cloudflare/wrangler.jsonc
  - cloudflare/test/rate-limit.test.js
links:
  - answers: q-rate-limiting
  - supports: dec-free-tier-only
  - depends_on: comp-auth-throttle
---
- ブレーキ: Workers Free でも使える Rate Limiting binding。接続元のアドレス（CF-Connecting-IP）ごとに、全体 10 秒 120 回（RL_ANY）、登録・ログイン・復旧 1 分 10 回（RL_AUTH）。ログインの確認（D1 を読む）より前に掛けるので、連打されても D1 の読み取りが増えない。D1 への書き込みは無い
- 限界: binding は Cloudflare の拠点ごとに数え、少し多めに通す（公式の説明は permissive・eventually consistent）。正確な数えではないので、保存が増えるもの（新規登録）だけは D1 で正確に上限を掛ける: 日本時間の 1 日に 200 件（`NEW_ACCOUNTS_PER_DAY` で変えられる）。users.created_at を数えるので、訪問者についての新しい記録は持たない
- binding が無い・壊れたときは通す（無料枠を守る仕組みでサービスを止めない）。復旧コードは 256 ビットなので総当たりの心配は無く、制限の目的は費用と濫用
- 未確認: 本番の workers.dev で binding が実際に 429 を返すか（S13）。公開の不具合報告に「workers.dev で制限が効かない」というものがあるので、deploy 後に実際に試す
