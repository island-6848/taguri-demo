---
id: workers-preview-build-log
type: finding
status: confirmed
date: 2026-10-14
title: master 以外のブランチの組み立ては `npx wrangler preview` を走らせ、設定に previews の欄が無いので失敗している
sources:
  - https://dash.cloudflare.com/e03256e9248f40014442896755e0c98b/workers/services/view/taguri-demo/production/builds/21f650d1-2236-4b5b-b804-ff05b463c2af
links:
  - answers: q-branch-builds-fail
  - supports: workers-builds-branch-fail
---
起案者が貼った組み立ての記録（2026-10-13 23:19 UTC、5072374）: bun install のあと「Executing user deploy command: npx wrangler preview」→「✘ [ERROR] Your Wrangler configuration is missing a `previews` block」で失敗。master 以外のブランチの組み立て（プレビュー）の配信の命令が `wrangler preview`（ベータ）になっていて、wrangler.jsonc に previews（プレビュー用の変数と D1）が無いため。本番（master）の命令は別なので影響しない。
直し方は 2 つ: (1) Cloudflare の Settings → Builds → Branch control で master 以外の組み立てを止める（勧め。✗ が消え、無料の組み立て時間も使わない）、(2) wrangler.jsonc に previews を足す ── ただしプレビューに本番の D1 を渡すと、試しの版が本番の記録に書けてしまうので、プレビュー用の D1 を別に作る必要がある（無料枠の中だが、管理するものが増える）。
