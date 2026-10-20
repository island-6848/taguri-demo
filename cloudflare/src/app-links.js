// Android アプリ（TWA、android/）とこのサイトを結び付ける /.well-known/assetlinks.json（plan-app-release、impl-android-twa）。
// アプリの署名の指紋（SHA-256）がここにあると、アプリはブラウザの帯なしの全画面で開く。無いうちは帯付きで開く（動きはする）。
// 指紋は秘密ではない（誰でもこの道で読める）。Google Play に上げたあと、Play Console の「アプリの完全性 → アプリ署名」にある
// 「アプリ署名鍵の証明書」の SHA-256 を足す（自分で端末に入れて確かめるときは、アップロード鍵の指紋も足す）。
// ログインの前に開けるよう、Worker が gate の前に答える（worker.js）
export const ANDROID_PACKAGE = 'jp.taguri.app';   // android/app/build.gradle.kts の applicationId と同じ
export const ANDROID_FINGERPRINTS = [];            // 'AB:CD:…' の形（64 桁の 16 進を : で区切る）

export function assetLinks(pkg = ANDROID_PACKAGE, fps = ANDROID_FINGERPRINTS) {
  if (!fps.length) return [];
  return [{relation: ['delegate_permission/common.handle_all_urls'],
    target: {namespace: 'android_app', package_name: pkg, sha256_cert_fingerprints: fps}}];
}

export const assetLinksResponse = () => new Response(JSON.stringify(assetLinks()), {
  headers: {'Content-Type': 'application/json', 'Cache-Control': 'public, max-age=3600'}});
