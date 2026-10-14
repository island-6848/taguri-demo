---
id: q-branch-builds-fail
type: question
status: answered
date: 2026-10-14
title: Workers Builds の master 以外のブランチの組み立てが毎回失敗するのはなぜか。止めてよいか
links:
  - affects: workers-builds-branch-fail
---
起案者に Cloudflare のダッシュボード（Workers & Pages → taguri-demo → Builds）で、失敗した組み立ての記録（ブランチ名とログ）を見てもらう。例: https://dash.cloudflare.com/e03256e9248f40014442896755e0c98b/workers/services/view/taguri-demo/production/builds/21f650d1-2236-4b5b-b804-ff05b463c2af 。master 以外のブランチの組み立て（プレビュー）が要らなければ、設定（Settings → Builds → Branch control）で master だけにすると、✗ が消え、組み立ての分（無料は月 3,000 分）も節約できる。あわせて本番の /api/health（workers.dev の URL）で、catalog と free_tier が返るかを見てもらう。
