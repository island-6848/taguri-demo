---
id: f-ios-web-push
type: finding
status: unverified
date: 2026-10-20
title: iPhone・iPad でも、ホーム画面に追加した Web アプリは通知（Web Push）を受け取れる（iOS 16.4 から）
sources:
  - https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/
  - https://www.webkit.org/?p=13966
links:
  - affects: q-app-direction
---
WebKit の公式ブログ（2023 年 2 月、iOS 16.4 ベータ 1）を、検索結果の引用で読んだだけなので unverified。

- ホーム画面に追加した Web アプリは、Push API・Notifications API・service worker で通知を受け取れる。Safari で開いているだけのページは通知の許可を求められない
- 許可は、ボタンを押すなど利用者の操作に応えてだけ求められる。ロック画面・通知センター・Apple Watch に出る。アイコンの数字（Badging API）も使える
- 分からないこと: 今の iOS での細かな制限（このあと変わったか）。通知を送る側（Worker から VAPID で送る）の無料枠の数え方は、作る前に Cloudflare の料金表で確かめる
