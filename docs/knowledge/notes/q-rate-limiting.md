---
id: q-rate-limiting
type: question
status: answered
date: 2026-10-13
title: ログイン・登録・検索の回数制限を Worker でどう掛けるか
links:
  - depends_on: comp-auth-throttle
  - affects: comp-cf-worker
---
セキュリティ点検の S3。Render 版は auth.py が IP ごとに数えていた。
