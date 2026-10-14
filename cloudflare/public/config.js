"use strict";
/* たぐり（本番・app.taguri.workers.dev）── web/config.js の代わり。
 *
 * 画面と API が同じサイトにある。画面の中身は Worker が D1 から組む（NATIVE_UI=all。
 * 2026-10-14 に Render のデモ版への中継をやめた〔dec-native-cutover-now〕）ので、サービス版として振る舞う。
 * api は同じサイト（Content-Security-Policy の connect-src 'self' に収まる）。 */
window.TAGURI = {edition: "service", api: location.origin, base: "", demoBase: "https://island-6848.github.io/taguri-demo"};
