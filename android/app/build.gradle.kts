// アプリの番号（applicationId）は Google Play に一度出すと変えられない。決めるのは起案者（plan-app-release）。
// 変えるときは cloudflare/src/app-links.js の ANDROID_PACKAGE も同じにする
plugins { id("com.android.application") }

// 署名（アップロード鍵）は GitHub の Secrets から環境変数で渡す（.github/workflows/android.yml）。鍵はリポジトリに入れない。
// 無いときは署名しない release と、確かめ用の debug だけを作る
val keystore: String? = System.getenv("TAGURI_KEYSTORE_FILE")

android {
    namespace = "jp.taguri.app"
    compileSdk = 35
    defaultConfig {
        applicationId = "jp.taguri.app"
        minSdk = 23
        targetSdk = 35
        // 出すたびに 1 ずつ上げる（Play は同じ番号を受け付けない）。ワークフローの入力で渡す
        versionCode = (System.getenv("TAGURI_VERSION_CODE") ?: "1").toInt()
        versionName = System.getenv("TAGURI_VERSION_NAME") ?: "1.0.0"
    }
    signingConfigs {
        if (keystore != null) create("upload") {
            storeFile = file(keystore)
            storePassword = System.getenv("TAGURI_KEYSTORE_PASSWORD")
            keyAlias = System.getenv("TAGURI_KEY_ALIAS")
            keyPassword = System.getenv("TAGURI_KEY_PASSWORD")
        }
    }
    buildTypes {
        release {
            isMinifyEnabled = false
            if (keystore != null) signingConfig = signingConfigs.getByName("upload")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies {
    // Chrome で画面を全画面に開く部品（Google の android-browser-helper）
    implementation("com.google.androidbrowserhelper:androidbrowserhelper:2.5.0")
}
