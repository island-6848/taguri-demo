"use strict";
/* たぐり（Cloudflare移行版）── web/config.js の代わり。
 *
 * 移行版は画面と API が同じサイトにある。画面の材料は Worker が Render のデモ版へ
 * 橋渡しする（src/original-ui.js）ので、版はデモ版として振る舞う。
 * api は同じサイト（Content-Security-Policy の connect-src 'self' に収まる）。 */
window.TAGURI = {edition: "demo", api: location.origin, base: "", demoBase: ""};
