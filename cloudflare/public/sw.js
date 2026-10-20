"use strict";
/* たぐりのアプリ（ホーム画面に入れたとき）の service worker（起案者 2026-10-20「アプリにしたい」、impl-pwa-base）。
 *
 * - 控えるのは画面の部品（CSS・JS・字・絵）だけ。**記録・答え・おすすめ（/api/）とポスター（/img/）は控えない**
 *   ── 人の記録を端末に残さず、古い記録を見せないため
 * - いつも先に取りに行き（network-first）、つながらないときだけ控えを使う。新しい版を出したのに古い app.js が残る、を起こさない
 * - 画面を開けないとき（通信が無い）は、その旨の 1 枚を出す
 * 控えの名前を変えると、前の控えは消える（activate）。 */
const CACHE = "taguri-shell-v1";
const SHELL = ["/style.css", "/theme.css", "/fonts.css", "/app.js", "/config.js", "/halfwidth.js", "/assets/logo/icon-192.png"];
const NEVER = /^\/(api|img|migration-api|oauth|login|export\.json|data\.zip)(\/|$)/;
const STATIC = /\.(css|js|woff2|png|svg|webmanifest)$/;
const OFFLINE = '<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
  + '<title>つながっていません ― たぐり</title><style>body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;'
  + 'background:#fbeee2;color:#1d1d1f;font-family:system-ui,sans-serif;text-align:center;padding:24px}button{margin-top:16px;padding:10px 20px;'
  + 'border:1px solid #1d1d1f;border-radius:999px;background:#fff;font-size:15px}</style></head><body><div>'
  + '<img src="/assets/logo/icon-192.png" alt="" width="96" height="96"><h1 style="font-size:20px">インターネットにつながっていません</h1>'
  + '<p>つながったら、もう一度開いてください。記録はたぐりのサーバーにあるので、消えていません。</p>'
  + '<button onclick="location.reload()">もう一度読み込む</button></div></body></html>';

self.addEventListener("install", ev => {
  // 1 つ取れなくても入れる（控えは次に開いたときにも足す）
  ev.waitUntil(caches.open(CACHE).then(c => Promise.all(SHELL.map(u => c.add(u).catch(() => null)))).then(() => self.skipWaiting()));
});
self.addEventListener("activate", ev => {
  ev.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", ev => {
  const req = ev.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== location.origin || NEVER.test(url.pathname)) return;   // ブラウザにそのまま任せる
  if (req.mode === "navigate") {
    ev.respondWith(fetch(req).catch(() => new Response(OFFLINE, {headers: {"Content-Type": "text/html; charset=utf-8"}})));
    return;
  }
  if (!STATIC.test(url.pathname)) return;
  ev.respondWith(fetch(req).then(res => {
    if (res.ok && res.type === "basic") { const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)); }
    return res;
  }).catch(() => caches.match(req).then(hit => hit || Response.error())));
});
