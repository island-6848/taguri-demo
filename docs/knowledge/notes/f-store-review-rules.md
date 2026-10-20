---
id: f-store-review-rules
type: finding
status: unverified
date: 2026-10-20
title: App Store は Web の画面を包んだだけのアプリを 4.2（最低限の機能）で落としやすい。Google Play の新しい個人アカウントは 12 人・14 日の非公開テストが要る。Android は PWA を TWA で包んで出せる
sources:
  - https://developer.apple.com/forums/thread/806726
  - https://www.mobiloud.com/blog/app-store-review-guidelines-webview-wrapper
  - https://support.google.com/googleplay/android-developer/answer/14151465
  - https://www.choicely.com/blog/google-play-12-tester-rule
  - https://www.thinktecture.com/en/pwa/twa-bubblewrap
  - https://developer.chrome.com/docs/android/trusted-web-activity/quick-start
links:
  - affects: plan-app-release
---
検索結果の引用で読んだだけ（Apple の審査ガイドラインの本文・Google のヘルプの本文は直接開けていない）ので unverified。

- **App Store（4.2 / 4.2.2 最低限の機能）**: Web の画面を WebView で包んだだけのアプリは「モバイルのブラウザで見るのと十分に違わない」として落とされやすい（Apple の開発者フォーラムの報告・解説記事）。通知・位置情報・共有だけでは足りないという定型文が返る報告がある。主な画面をネイティブで作る（WebView を主にしない）のが確かな道とされる
- **Google Play の非公開テスト**: 2023 年 11 月 13 日より後に作った個人の開発者アカウントは、本番に出す前に、12 人以上が 14 日続けて参加した非公開テストが要る（Google のヘルプの引用。前は 20 人で、2024 年 12 月に 12 人へ、と第三者の解説）。組織のアカウントにはかからない（第三者の解説）
- **TWA（Trusted Web Activity）**: PWA をほぼ空の Android アプリで包み、Play に出せる。サイトの /.well-known/assetlinks.json に、Play が署名する鍵の指紋を置いて結び付ける（合わないとブラウザの帯が出る）。中で使えるのは Web の機能だけ。Bubblewrap で作れる
- 分からないこと: Apple の審査の今の運用の細部。たぐりの画面のどこまでをネイティブにすれば通るか
