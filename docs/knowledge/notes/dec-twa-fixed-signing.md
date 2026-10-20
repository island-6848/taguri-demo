---
id: dec-twa-fixed-signing
type: decision
status: adopted
date: 2026-10-20
title: アプリの上の URL と ✕ の帯を消すため、固定のアップロード鍵で debug も release も署名し、その指紋を assetlinks.json に載せる（WebView には替えない）
sources:
  - cloudflare/src/app-links.js
  - android/app/build.gradle.kts
  - .github/workflows/android.yml
  - https://developer.chrome.com/docs/android/trusted-web-activity/integration-guide
links:
  - affects: impl-android-twa
  - affects: plan-app-release
---
起案者（2026-10-20）「アプリ開いて上に×ボタンのあるナビゲーションバーでるのなぜ？ちゃんとこれ単体で動くアプリ化」。

- 理由: TWA は、サイトの /.well-known/assetlinks.json にアプリの署名の指紋（SHA-256）があるときだけ帯なしの全画面で開く。合わないと Chrome は URL と ✕ の付いた Custom Tab に戻す。いまは指紋が空だった。さらに CI は実行のたびに新しい debug 鍵を作るので、debug APK の指紋は毎回変わっていた
- 決めたこと: アップロード鍵（PKCS12、別名 upload、2054 年まで有効）を作り、Secrets（TAGURI_UPLOAD_*）から debug と release の両方をこの鍵で署名する。指紋 29:3D:…:1E:64 を app-links.js の ANDROID_FINGERPRINTS に載せた。ワークフローの「Signing fingerprint」の段が、APK の指紋と、それがサイトに載っているかを実行の要約に出す。テストで指紋の形と、実際に返していることを確かめる
- 鍵はリポジトリに入れない。起案者が Secrets に入れ、.jks を手元に控える
- Play で配るときは Google が別の鍵（アプリ署名鍵）で署名し直すので、Play Console の SHA-256 も足す（まだ）
- 自前の WebView（Capacitor など）にしなかった理由: WebView の中では Google のログインが使えず（disallowed_useragent）、パスキーも使いにくい。TWA なら Chrome のログイン・パスキー・通知がそのまま使える。ただし iPhone では TWA が無いので、そのときに改めて考える〔plan-app-release〕
- 分からないこと: 実機で帯が消えるかは、起案者が Secrets を入れて組み直した APK を入れ直すまで確かめられない。Chrome は確かめた結果をしばらく控えるので、入れ直しが要ることがある
