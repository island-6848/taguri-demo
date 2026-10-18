---
id: q-fav-same-production
type: question
status: answered
date: 2026-10-18
title: お気に入りの一覧に出ている公演と同じ公演（別の番号）を、おすすめから外すべきか
sources:
  - cloudflare/src/screens/recommend.js
links:
  - depends_on: fix-reason-no-paren
---
fix-reason-no-paren で、作品名がカードの公演そのものしか無い理由の行が出ていた原因の 1 つは、同じ公演が別の番号（会場・ツアーの鍵の違い）でお気に入りの一覧や種にあることだった。sameProduction は答えた公演（興味あり・興味なし・購入済・行けない）とだけ照らしている。お気に入りの種（多くて 60 公演）も照らせば外せるが、D1 の読み取りが種の数だけ増える（rec_stage の主キーの行）。本番でどれだけ起きているかを確かめてから決める。
