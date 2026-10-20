// リンクを X・LINE などに貼ったときのカード（起案者の指示 2026-10-19「Twitterとかで共有した時に出るURLのカード？みたいなやつ設定して」）。
// どのページの HTML にも OGP と X のカードの meta を足し、ログインしていないクローラーにはその場でログインの画面を返す。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import worker from '../src/worker.js';
import {cardMeta, PREVIEW_BOT} from '../src/link-card.js';

const ORIGIN = 'https://taguri.example';
// HTMLRewriter (Workers only) for the tags this file needs: append to <head> / <body>, remove an element by id
class FakeRewriter {
  constructor() { this.rules = []; }
  on(sel, h) { this.rules.push([sel, h]); return this; }
  transform(res) {
    const run = async () => {
      let html = await res.text();
      for (const [sel, h] of this.rules) {
        const el = {append: s => { html = html.replace(`</${sel}>`, s + `</${sel}>`); }, remove: () => {}};
        if (sel === 'head' || sel === 'body') h.element(el);
      }
      return html;
    };
    const body = new ReadableStream({async start(c) { c.enqueue(new TextEncoder().encode(await run())); c.close(); }});
    return new Response(body, {status: res.status, headers: res.headers});
  }
}
const page = '<!doctype html><html><head><title>x</title></head><body></body></html>';
const env = {ASSETS: {fetch: async () => new Response(page, {headers: {'content-type': 'text/html'}})},
  DB: {prepare: () => ({bind() { return this; }, async first() { return null; }, async all() { return {results: []}; }, async run() { return {}; }})}};
const get = (path, ua = '') => worker.fetch(new Request(ORIGIN + path, {headers: ua ? {'user-agent': ua} : {}}), env);

test('the card tags: absolute image on this origin, large image card, nothing of a user', () => {
  const m = cardMeta(ORIGIN);
  assert.match(m, /<meta property="og:image" content="https:\/\/taguri\.example\/assets\/og\.png">/);
  assert.match(m, /<meta name="twitter:card" content="summary_large_image">/);
  assert.match(m, /<meta property="og:title" content="たぐり ― 観劇の記録から、次の一本を">/);
  assert.match(m, /<meta property="og:url" content="https:\/\/taguri\.example\/">/);
  // the image is in public/ and is 1200×630 (PNG header)
  const png = readFileSync(new URL('../public/assets/og.png', import.meta.url));
  assert.deepEqual([png.readUInt32BE(16), png.readUInt32BE(20)], [1200, 630]);
});

test('a link-preview crawler gets the sign-in page with the card instead of a redirect; people still get the redirect', async () => {
  globalThis.HTMLRewriter = FakeRewriter;
  try {
    for (const ua of ['Twitterbot/1.0', 'facebookexternalhit/1.1;line-poker/1.0', 'Slackbot-LinkExpanding 1.0', 'Mozilla/5.0 (compatible; Discordbot/2.0)']) {
      assert.ok(PREVIEW_BOT.test(ua), ua);
      const r = await get('/recommend?x=1', ua);
      assert.equal(r.status, 200, ua);
      assert.match(await r.text(), /<meta name="twitter:card" content="summary_large_image">.*<\/head>/s, ua);
    }
    const person = await get('/recommend', 'Mozilla/5.0 (iPhone) Safari/605.1');
    assert.equal(person.status, 302);
    // the public pages (ログイン・規約) carry the card for everyone
    assert.match(await (await get('/terms')).text(), /og:image/);
    assert.equal((await get('/assets/og.png', 'Twitterbot/1.0')).status, 200);
  } finally { delete globalThis.HTMLRewriter; }
});

// robots.txt が無いと、アプリの HTML（single-page-application の受け皿）が robots.txt として返っていた。クローラーが読める本物を置く
test('robots.txt is a real file that lets the card crawlers in', () => {
  const t = readFileSync(new URL('../public/robots.txt', import.meta.url), 'utf8');
  assert.match(t, /^User-agent: \*$/m);
  assert.match(t, /^Allow: \/$/m);
  assert.doesNotMatch(t, /^Disallow: \/\s*$/m);
});

// アプリとしてホーム画面に入れる（起案者 2026-10-20「アプリにしたい」、impl-pwa-base）
test('the app manifest, its icons, the head tags, and a service worker that never keeps records', async () => {
  const m = JSON.parse(readFileSync(new URL('../public/manifest.webmanifest', import.meta.url), 'utf8'));
  assert.equal(m.display, 'standalone');
  assert.equal(m.lang, 'ja');
  assert.ok(m.start_url.startsWith('/recommend'));
  for (const ic of m.icons) {
    const png = readFileSync(new URL('../public' + ic.src, import.meta.url));
    assert.equal(`${png.readUInt32BE(16)}x${png.readUInt32BE(20)}`, ic.sizes, ic.src);
  }
  assert.ok(m.icons.some(ic => ic.purpose === 'maskable'));
  const {APP_HEAD} = await import('../src/link-card.js');
  assert.match(APP_HEAD, /<link rel="manifest" href="\/manifest\.webmanifest">/);
  globalThis.HTMLRewriter = FakeRewriter;
  try { assert.match(await (await get('/terms')).text(), /rel="manifest"[^]*<\/head>/); } finally { delete globalThis.HTMLRewriter; }
  const sw = readFileSync(new URL('../public/sw.js', import.meta.url), 'utf8');
  const never = new RegExp(sw.match(/const NEVER = \/(.+)\/;/)[1]);
  for (const p of ['/api/screen/recommend', '/api/react', '/img/1.jpg', '/login', '/export.json']) assert.ok(never.test(p), p);
  for (const p of ['/app.js', '/style.css', '/recommend']) assert.ok(!never.test(p), p);
});
