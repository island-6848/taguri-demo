---
id: q-free-tier-account-settings
type: question
status: open
date: 2026-10-13
title: 起案者のアカウントの設定で、無料枠を越えても請求されないようになっているか
links:
  - affects: dec-free-tier-only
---
コードの上限とは別に、起案者に画面で確かめてもらうこと:
1. GitHub → Settings → Billing and licensing: Actions の予算が 0 ドルで「Stop usage when budget limit is reached」が有効か（gha-minutes-reset-budget）。taguri-crawler 以外の非公開リポジトリで Actions を使っていないか（2,000 分はアカウント全体の数。たぐりは 1,500 分までにして 500 分を残している）
2. Cloudflare → Manage Account → Billing → Billable Usage: Budget alerts を 0.01 ドルで作る（R2 で 1 円でも請求が出たらメールが来る。止めはしない。cf-budget-alerts-not-cap）
3. Cloudflare の Workers のプランが Free のままか
