# Android アプリを Google Play に出す手順

たぐりの Android アプリは、`https://app.taguri.workers.dev` の画面を Chrome で全画面に開く薄い入れ物（TWA: Trusted Web Activity）です。
画面の中身はサイトと同じなので、サイトを直すとアプリにもそのまま出ます（アプリを出し直さなくてよい）。
計画は〔plan-app-release〕、作り方は〔impl-android-twa〕。

費用は Google Play の登録料（最初に 1 回 25 米ドル）だけで、起案者が負担します〔dec-app-release-costs〕。組むのは公開リポジトリの GitHub Actions（無料）です。

## 起案者にしてもらうこと

1. **アプリの番号（パッケージ名）を決める。** いまは仮に `jp.taguri.app`。**Play に一度上げると変えられません。** 変えるなら上げる前に知らせてください（`android/app/build.gradle.kts` と `cloudflare/src/app-links.js` の 2 か所を直します）
2. **Google Play Console の開発者アカウントを作る**（https://play.google.com/console ）。登録料 25 米ドル、本人確認（身分証）があります。
   - **個人**のアカウントだと、本番に出す前に **12 人以上が 14 日続けて参加する非公開テスト**が要ります〔f-store-review-rules〕。テストに入ってくれる人（Google アカウントのメールアドレス）を 12 人以上集めておくと早く進みます
   - **組織**のアカウントは、この条件がかからないと言われています（D-U-N-S 番号などが要ります）
3. **アップロード鍵を作って、GitHub の Secrets に入れる。** 鍵はリポジトリに入れません。手元に Java があれば次の 1 行で作れます（合言葉は自分で決めて、なくさないように控えてください）:
   ```
   keytool -genkeypair -v -keystore taguri-upload.jks -alias upload -keyalg RSA -keysize 2048 -validity 10000
   ```
   リポジトリの Settings → Secrets and variables → Actions に、次の 4 つを入れます:
   - `TAGURI_UPLOAD_KEYSTORE_B64`: `base64 -w0 taguri-upload.jks`（Mac は `base64 -i taguri-upload.jks`）の出力
   - `TAGURI_UPLOAD_KEYSTORE_PASSWORD`: 鍵の保管庫の合言葉
   - `TAGURI_UPLOAD_KEY_ALIAS`: `upload`
   - `TAGURI_UPLOAD_KEY_PASSWORD`: 鍵の合言葉
   `taguri-upload.jks` は手元の安全な場所に残してください（なくすと Play の手続きで鍵を替えることになります）
4. **アプリを組む**: GitHub の Actions → Android → Run workflow（番号 1、版 1.0.0）。終わると「Artifacts」に、確かめ用の APK と、Play に上げる AAB ができます
5. **Play Console でアプリを作り、AAB を「内部テスト」に上げる。** 「アプリの完全性 → アプリ署名」に出る **アプリ署名鍵の SHA-256 証明書フィンガープリント**を知らせてください。サイトの `/.well-known/assetlinks.json` に足すと、アプリからブラウザの帯が消えます
6. **ストアの掲載情報**: アプリの説明・アイコン（512×512。`web/assets/logo/icon-512.png`）・フィーチャーグラフィック（1024×500）・スクリーンショット・プライバシーポリシーの URL（`https://app.taguri.workers.dev/privacy`）・データセーフティ・コンテンツのレーティング・アカウント削除の案内（アプリの「アカウント」の画面と `https://app.taguri.workers.dev/account`）。文面と画像の下書きは Claude が用意できます
7. **非公開テスト（個人アカウントのとき）**: 12 人以上を招いて 14 日 → 本番へのアクセスを申請 → 審査 → 公開

## 確かめ用の APK を自分の Android に入れる

Artifacts の `app-debug.apk` を端末に送って開くと入ります（「提供元不明のアプリ」を許可する必要があります）。
署名の指紋がまだサイトに無いので、上にブラウザの帯が出ますが、動きは同じです。
