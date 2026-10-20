---
id: plan-app-release
type: question
status: open
date: 2026-10-20
title: アプリ化の計画（PWA を土台に、Android は TWA、iPhone はネイティブの画面を持つアプリ）と、起案者に決めてもらうこと
links:
  - depends_on: dec-app-release-costs
  - depends_on: f-store-review-rules
  - depends_on: f-ios-web-push
---
段:
1. **PWA の土台**（無料・ストア不要。Android の TWA にも iPhone のアプリにも要る）: manifest・アイコン・service worker（画面の部品だけ。記録は控えない）・通信が無いときの画面。2026-10-20 に着手〔impl-pwa-base〕
2. **Android（Google Play）**: TWA で包む。assetlinks.json を Worker で配る。個人アカウントなら 12 人・14 日の非公開テスト
3. **通知（Web Push）**: 開幕リマインド・発売日・お気に入りの新着。無料枠（D1 の書き込み・cron・CPU 10 ミリ秒）を数えてから
4. **iPhone（App Store）**: Web を包んだだけでは 4.2 で落ちやすいので、主な画面（おすすめ・興味あり・評価）をネイティブで作る。ビルドと提出に Mac と Xcode が要る

2026-10-20 起案者「Androidから先に出したい」→ 段 2 に着手〔impl-android-twa〕。

起案者に決めてもらうこと: Mac を使えるか（iPhone のアプリのビルドに要る）／先に出すのは Android か iPhone か／開発者アカウントを個人で取るか組織で取るか（Google の非公開テストの条件が変わる）／独自ドメインにするか（パスキー・アプリの結び付けがドメインに付くので、出す前に決める）
