---
id: f-app-store-fees
type: finding
status: unverified
date: 2026-10-20
title: ストアに出すには登録料がかかる（App Store は年 99 米ドル、Google Play は最初に 25 米ドル）。ホーム画面に入れる Web アプリ（PWA）はかからない
sources:
  - https://developer.apple.com/support/membership-fee-waiver/
  - https://support.google.com/googleplay/android-developer/answer/6112435
  - https://studio.adalo.com/blog/apple-developer-program-guide
links:
  - affects: q-app-direction
---
起案者の希望（2026-10-20）「本格的にアプリ化に進みたい」を受けて調べた。公式ページはこの環境から開けず、**検索結果に出た公式ページの引用だけを見ている**ので unverified。

- Apple Developer Program: 年 99 米ドル（現地通貨のことも）。払わないとストアからアプリが外れる（第三者の解説）。公式の免除のページには「免除が外れたら年 99 米ドル」とある。免除は非営利・教育機関・行政で、個人は対象外（第三者の解説）
- Google Play Console: 登録のとき 1 回 25 米ドル（公式のヘルプの引用）
- どちらも有料なので、たぐりの約束（無料の範囲、有料のプランは使わない・勧めない。変えられるのは起案者だけ）では使えない。ホーム画面に入れる Web アプリ（PWA: manifest と service worker）は、今の Cloudflare の配信だけでできて料金はかからない
