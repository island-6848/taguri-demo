---
id: gha-minutes-reset-budget
type: finding
status: confirmed
date: 2026-10-13
title: Actions の無料の分は毎月 0 に戻り、月払いの支払いの上限は既定で 0 ドル（越えると止まる）
sources:
  - https://docs.github.com/en/billing/concepts/product-billing/github-actions
  - https://docs.github.com/en/billing/reference/product-usage-included
links:
  - supports: gha-private-free-minutes
  - supports: dec-free-tier-only
---
GitHub の公式の説明（検索結果の引用で確かめた）。GitHub Free は非公開リポジトリで月 2,000 分。使った分は毎月の始めに 0 に戻る（保存容量は戻らない）。月払いの利用者は支払いの上限が既定で 0 ドルで、含まれる分を越えると非公開リポジトリの実行が止まる。別の説明では「予算を作り『上限で止める（Stop usage when budget limit is reached）』を有効にしていなければ請求される」ともあり、**今の請求の仕組みでどちらが当てはまるかは、起案者の GitHub の Billing の画面で確かめる必要がある**（q-free-tier-account-settings）。支払い方法が登録されていなければ、使い切った時点で止まる、とも書かれている。
2,000 分は **アカウント全体** の数。taguri-crawler 以外の非公開リポジトリで Actions を使っていれば、その分も減る。公開リポジトリ（taguri-demo）の標準の実行環境は無料（github-actions-public-free）。
