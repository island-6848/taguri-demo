---
id: dec-d1-catalogue-delivery
type: decision
status: adopted
date: 2026-10-13
title: 取得処理のあとに、変わった公演の行だけを wrangler で本番の D1 に入れる
sources:
  - cloudflare/scripts/deliver_catalogue.py
  - tools/taguri/deploy/github-actions/catalog.yml
  - https://claude.ai/code/session_015xXsQ9C4423EMquRbg7m3U （起案者の指示「D1に入れる段も進めて」）
links:
  - answers: q-catalog-to-worker
  - depends_on: dec-crawler-gha-private
  - depends_on: dec-synopsis-reader-claude
  - depends_on: dec-workers-d1
  - raises: q-catalogue-api-limit
  - raises: q-catalogue-python-snapshot-vs-d1
verifies:
  - S21
  - S23
---
起案者の指示（2026-10-13）。taguri-crawler の取得のあと、deliver_catalogue.py が終わっていない公演を、いまの本番 Worker が読む catalogue 表の形（convert_catalogue.public_candidate、公開の欄だけ）にし、themes.jsonl の候補側のあらすじと内容の要素を metadata に入れる。
前回入れた行のハッシュを data/d1/delivered.json（state ブランチ）に持ち、変わった行だけ upsert する。消さない（記録が結び付いた公演の名前が消えないように）。wrangler が成功してから commit で控えを更新するので、失敗した分は次回まるごと入れ直す。
書き込みは 1 行につき索引と合わせて 2 行と見積もり、1 日 6 万行を超えるなら入れる前に止める（D1 の無料枠 10 万行の残りは利用者の操作のため）。推薦の索引（build_recommend_index.py）は版が変わり、枠に収まるときだけ入れる。
rec_meta に catalogue_scan・catalogue_delivered・catalogue_upcoming を書き、Worker の公開の /api/health が日付と件数だけを返す。catalog-age.yml はその URL を毎日見る（変数 TAGURI_HEALTH_URL は起案者が 2026-10-13 に入れた。日本時間 9:43 に動く）。
Cloudflare の鍵（CLOUDFLARE_API_TOKEN・CLOUDFLARE_ACCOUNT_ID）は taguri-crawler の Secrets に入っている（起案者が 2026-10-13 に確かめた）。
テスト（cloudflare/test/test_deliver_catalogue.py・worker.test.js）は通ったが、本番の D1 にはまだ一度も入れていない。初回の結果で q-catalog-to-worker を閉じる。
