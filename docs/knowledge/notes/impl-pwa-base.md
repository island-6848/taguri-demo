---
id: impl-pwa-base
type: decision
status: adopted
date: 2026-10-20
title: アプリ化の土台（PWA）: manifest・アイコン・service worker（画面の部品だけを控え、記録は控えない）・通信が無いときの画面
sources:
  - cloudflare/public/manifest.webmanifest
  - cloudflare/public/sw.js
  - cloudflare/public/_headers
  - cloudflare/src/link-card.js
  - web/app.js
  - web/assets/logo/icon-192.png
  - docs/design/logo/make_app_icons.mjs
  - cloudflare/test/link-card.test.js
links:
  - depends_on: dec-app-release-costs
  - affects: plan-app-release
  - affects: comp-cf-worker
---
起案者の指示（2026-10-20）「本格的に配信リリースするときの経費は負担する。アプリにしたい。」の第 1 段〔plan-app-release〕。Android の TWA にも iPhone のアプリにも要る土台で、ストアは使わない。

- manifest（/manifest.webmanifest）: 名前「たぐり」、開く画面 /recommend、全画面（standalone）、縦向き、地の色 #fbeee2。アイコンは 192・512 と、Android の丸や角丸に切られても欠けない maskable 512（make_type.py のオペラグラスから make_app_icons.mjs で作る）
- 頭の印: Worker が配る HTML に manifest・theme-color・iPhone 向けの apple-mobile-web-app-* を足す（link-card.APP_HEAD。カードの meta と同じ所）
- service worker（/sw.js、サービス版だけ登録。デモの GitHub Pages では入れない）: 控えるのは CSS・JS・字・絵だけ。**/api/（記録・答え・おすすめ）と /img/（ポスター）・ログインは控えない**（人の記録を端末に残さない・古い記録を見せない）。いつも先に取りに行き、つながらないときだけ控えを使う（新しい版を出したのに古い app.js が残る、を起こさない）。画面を開けないときは「インターネットにつながっていません」の 1 枚。sw.js と manifest は Cache-Control: no-cache
- 確かめたこと: Worker のテスト（manifest・アイコンの大きさ・頭の印・控えない道）。手元で Worker をテストのデータで動かし Chromium で開いて、service worker が入り、画面の部品だけが控えに入り、通信を切って開き直すと通信が無いときの画面が出た。本番の iPhone・Android で「ホーム画面に追加」して開くのは、まだ試していない
- 無料枠: 静的ファイルが 4 つ増えるだけ。service worker は先に取りに行くので、Worker への要求は増えない
