---
id: q-pr14-free-tier
type: question
status: open
date: 2026-10-14
title: 推薦側の PR #14（回数制限・見張り・D1 の控え・CPU の測定）が無料枠に収まるか。取得のジョブにどう載せるか
sources:
  - https://github.com/island-6848/taguri-demo/pull/14
links:
  - affects: dec-free-tier-only
  - affects: crawler-actions-minutes
---
別のセッション（session_011h35PdoJgoX8yQQagUsiJf、2026-10-14 04:19 UTC の知らせ。情報として扱う）。PR #14（claude/demo-records-setup-yqo65u、マージは起案者）に入っているもの:
1. Worker の回数制限（rate-limit.js、wrangler.jsonc の ratelimits: RL_ANY 10 秒 120 回・RL_AUTH 1 分 10 回）と、新規登録 1 日 200 件まで。超えると 429／503（JSON の error）。画面は post() が「できませんでした: <error>」と出すので、そのまま文が出る
2. service-watch.yml（1 時間ごと。公開リポジトリなので Actions は無料）、catalog-age の上限を 1 日に
3. D1 の控え（backup_d1.py、Catalog に「Back up the user records」の段、restore-drill.yml の雛形。BACKUP_PASSPHRASE が無ければ何もしない）
4. Catalog に Worker の推薦の CPU を測る段（measure_worker.mjs）。試験の小さな索引でも中央値 2〜9 ms・最大 50 ms と、無料の 10 ms に近い
確かめること（入ったら、取得のジョブに写す前に）:
- 段が増えるぶん Catalog のジョブが長くなる。free_tier.py の CATALOG_MINUTES（毎日 15 分の見積もり）を越えないか。越えるなら見積もりを直す
- 控えをどこに置くか（state ブランチ・R2・Actions の成果物）。R2 なら保存の上限（8 GB）と Class A に数える必要がある。Actions の成果物の保存は、非公開リポジトリだと無料枠（GitHub Free は 500 MB）を使う
- Worker の rate limiting の binding が無料プランで使えるか（公式で確かめる）
- 消した人の記録が暗号化した控えに最大 30 日残る（Time Travel は 7 日）── アカウントの削除の説明の文言を直す（q-restore-redelete）
- CPU が 10 ms を越える画面は、有料にせず Render のままにする（dec-free-tier-only）
