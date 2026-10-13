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
2026-10-14 追記: 起案者によると、GitHub には支払い方法を登録していない。GitHub の説明（gha-minutes-reset-budget）では、支払い方法が無ければ含まれる分を使い切った時点で止まる。だから **GitHub からは請求されない**（1 は済み。予算の設定は確かめなくてよい）。ただし 2,000 分を使い切ると、月末まで取得が止まり、公演一覧が古くなる。それを避けるため、上限 1,500 分はそのまま残す。
請求されうるのは、支払い方法を登録した Cloudflare（R2）だけ。2 と 3 はまだ確かめていない。
