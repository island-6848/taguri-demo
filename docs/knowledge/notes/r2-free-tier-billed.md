---
id: r2-free-tier-billed
type: finding
status: confirmed
date: 2026-10-13
title: R2 の無料枠は保存 10 GB・Class A 月 100 万回・Class B 月 1,000 万回で、越えた分は請求される（取り出しの通信料は無料）
sources:
  - https://developers.cloudflare.com/r2/pricing/
links:
  - verifies: r2-free-tier
  - supports: dec-free-tier-only
  - affects: dec-posters-r2
---
Cloudflare の R2 の料金ページ（検索結果の引用で確かめた。この作業環境からはページを直接開けない ── WebFetch が名前解決に失敗）。
- 無料枠（Standard の保存だけ）: 保存 10 GB-月、Class A（書き込み・一覧など）月 100 万回、Class B（読み出しなど）月 1,000 万回
- 越えた分: 保存 1 GB あたり 0.015 ドル、Class A 100 万回あたり 4.50 ドル、Class B 100 万回あたり 0.36 ドル。**止まらずに請求される**（D1・Workers の無料プランは上限で止まるだけ）
- 取り出しの通信料（egress）は無料
分からないこと: 失敗した PUT が Class A に数えられるか（たぐりは数えられる前提で、送る前に数える）。ダッシュボードの操作（バケットの一覧など）も Class A に入るはずだが、回数は数えていない。
