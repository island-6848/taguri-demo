---
id: cf-budget-alerts-not-cap
type: finding
status: confirmed
date: 2026-10-13
title: Cloudflare には R2 の使いすぎを止める仕組みが無い。予算の通知（Budget alerts）は知らせるだけ
sources:
  - https://developers.cloudflare.com/billing/manage/budget-alerts/
  - https://developers.cloudflare.com/changelog/post/2026-04-13-billable-usage-dashboard-and-budget-alerts/
links:
  - supports: dec-free-tier-only
  - raises: q-free-tier-account-settings
---
公式の説明（検索結果の引用で確かめた）。Manage Account → Billing → Billable Usage で、使った分の金額が決めた額を越えたらメールで知らせる「Budget alerts」を作れる（従量課金のアカウントだけ）。**知らせるだけで、止めはしない。** 製品ごとの量の通知は Notifications の「usage notifications」。R2 を止められるのは、たぐりのコードの上限（free_tier.py・free-tier.js）だけなので、それを守りの本体にし、Budget alerts を 0.01 ドルで作ってもらうのを最後の見張りにする。通知が「越えたとき」か「越えそうな見込みのとき」かは、公式の説明と変更履歴で食い違っている。
