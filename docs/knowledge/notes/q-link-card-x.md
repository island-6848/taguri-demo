---
id: q-link-card-x
type: question
status: answered
date: 2026-10-19
title: X にリンクのカードが出ない（2026-10-19、起案者の報告）。何が原因か
sources:
  - cloudflare/src/link-card.js
  - cloudflare/public/robots.txt
links:
  - depends_on: dec-link-card
---
起案者の報告（2026-10-19）「Twitterにでない」。

この環境からは本番（app.taguri.workers.dev）に届かず（プロキシが 403）、クローラーが何を受け取っているかを見られていない。考えられること:
- robots.txt が無く、アプリの HTML（single-page-application の受け皿）が返っていた → 本物の robots.txt（全部許可）を置いた
- 本番への配信（Workers Builds）が終わっていない、または失敗した。GitHub からは見えない
- X は同じ URL のカードをしばらく控える。配信の前に貼った URL は、カードの無い形が残っている
- 投稿の入力欄ではカードが出ず、投稿してから出ることがある（未確認）

確かめること: Cloudflare のダッシュボードで最新のデプロイが成功しているか。`https://app.taguri.workers.dev/?v=2` のように、まだ貼ったことのない形の URL で試す。
