---
id: impl-android-twa
type: decision
status: adopted
date: 2026-10-20
title: Android アプリは TWA（Chrome で app.taguri.workers.dev を全画面に開く入れ物）で作り、GitHub Actions で組む
sources:
  - android/app/build.gradle.kts
  - android/app/src/main/AndroidManifest.xml
  - .github/workflows/android.yml
  - cloudflare/src/app-links.js
  - cloudflare/src/worker.js
  - docs/android-release.md
  - docs/design/logo/make_android_icons.mjs
links:
  - depends_on: impl-pwa-base
  - depends_on: f-store-review-rules
  - affects: plan-app-release
---
起案者の指示（2026-10-20）「Androidから先に出したい」。

- android/: Gradle（AGP 8.7.3・Gradle 8.10.2・compileSdk/targetSdk 35・minSdk 23）と Google の android-browser-helper 2.5.0 の LauncherActivity。開く画面は /recommend?source=android、縦向き、地の色 #FBEEE2、app.taguri.workers.dev のリンクをこのアプリで開く。アイコンは make_type.py のオペラグラスから mipmap の各密度と adaptive icon の前景を作った
- アプリの番号（applicationId）は仮に jp.taguri.app。**Play に上げると変えられない**ので、起案者が決める（android/app/build.gradle.kts と cloudflare/src/app-links.js の 2 か所。テストでそろっているかを見る）
- 組むのは GitHub Actions（.github/workflows/android.yml。手で動かすか android/ を変えて master に押すと動く）。**この環境から Google の配布元（dl.google.com）に届かず、手元では組めない**ため。公開リポジトリの標準の実行環境は無料。debug APK と release AAB を Artifacts に 14 日置く。アップロード鍵は Secrets から（無ければ release は署名しない）。鍵はリポジトリに入れない（.gitignore で *.jks を外す）
- サイトの /.well-known/assetlinks.json を Worker が gate の前に返す（app-links.js）。指紋が無いうちは空の配列で、アプリは帯付きで開く。Play のアプリ署名鍵の SHA-256 を起案者から受け取って足す
- 起案者の手順は docs/android-release.md
- 分からないこと: Play の今の targetSdk の決まり（35 で足りるか）と、TWA の中での Google ログイン（Firebase）の動き。

2026-10-20: 初めての実行（Android #1、https://github.com/island-6848/taguri-demo/actions/runs/39372332177）が成功し、Artifacts に taguri-android-1（約 1 MB。debug APK と署名なしの release AAB）ができた。実機で開くのはまだ試していない。

2026-10-20: 起案者が実機で開くと、上に URL と ✕ の帯が出た。指紋が空で、debug APK が実行のたびに使い捨ての鍵で署名されていたため。固定のアップロード鍵で debug・release とも署名し、その指紋を assetlinks.json に載せる形に直した〔dec-twa-fixed-signing〕。
