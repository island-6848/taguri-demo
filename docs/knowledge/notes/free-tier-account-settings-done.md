---
id: free-tier-account-settings-done
type: finding
status: unverified
date: 2026-10-14
title: 起案者が Cloudflare の Budget alerts を作り、Workers の Free を確かめた。GitHub には支払い方法を登録していない
links:
  - answers: q-free-tier-account-settings
  - supports: dec-free-tier-only
---
起案者の報告（2026-10-14「やったよ」。q-free-tier-account-settings の 2・3 への答え）と、その前の「そもそもgithubに支払い情報入れてないから勝手に引き落としできないかも」。設定の画面は見ていないので unverified にした。GitHub は支払い方法が無いので、無料の分を使い切ると止まるだけで請求されない（gha-minutes-reset-budget）。請求されうるのは R2 だけで、Budget alerts（知らせるだけ）とコードの上限（dec-free-tier-only）で守る。
