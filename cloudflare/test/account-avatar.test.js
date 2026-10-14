// アカウントのアイコン画像（起案者の指示 2026-10-14）: a small WebP / JPEG / PNG as a data: URL,
// checked by its first bytes; anything else (SVG, a renamed text, too long) is refused.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {setup, signIn, step} from './screens/harness.js';

const b64 = bytes => Buffer.from(bytes).toString('base64');
const WEBP = 'data:image/webp;base64,' + b64([...Buffer.from('RIFF'), 0x20, 0, 0, 0, ...Buffer.from('WEBPVP8 '), ...new Array(40).fill(1)]);
const JPEG = 'data:image/jpeg;base64,' + b64([0xff, 0xd8, 0xff, 0xe0, ...new Array(40).fill(2)]);

test('the icon is saved, shown only to its owner, and removed', async () => {
  const {env, sqlite} = setup();
  try {
    const a = await signIn(env), b = await signIn(env);
    assert.match((await step(env, a, {get: '/api/screen/account'})).body.body_html, /data-account-avatar hidden/);
    const put = await step(env, a, {post: '/api/account', body: {avatar: WEBP}});
    assert.equal(put.status, 200);
    const html = (await step(env, a, {get: '/api/screen/account'})).body.body_html;
    assert.ok(html.includes(`<div class="acav" aria-hidden="true"><img src="${WEBP}" alt=""></div>`));
    assert.doesNotMatch((await step(env, b, {get: '/api/screen/account'})).body.body_html, /<img src="data:/);
    assert.equal((await step(env, a, {post: '/api/account', body: {avatar: JPEG}})).status, 200);
    // The display name is kept apart.
    await step(env, a, {post: '/api/account', body: {display_name: '観る人'}});
    assert.ok((await step(env, a, {get: '/api/screen/account'})).body.body_html.includes(JPEG));
    assert.equal((await step(env, a, {post: '/api/account', body: {avatar: ''}})).status, 200);
    assert.doesNotMatch((await step(env, a, {get: '/api/screen/account'})).body.body_html, /<img src="data:/);
  } finally { sqlite.close(); }
});

test('not an image, an SVG, or too large is refused', async () => {
  const {env, sqlite} = setup();
  try {
    const a = await signIn(env);
    for (const bad of ['data:image/svg+xml;base64,' + b64(Buffer.from('<svg onload=alert(1)>')),
      'data:image/png;base64,' + b64(Buffer.from('not a png at all......')),
      'data:image/webp;base64,' + b64(Buffer.from('RIFF....WEBP')) + 'A'.repeat(60000),
      'javascript:alert(1)', 42]) {
      const r = await step(env, a, {post: '/api/account', body: {avatar: bad}});
      assert.ok(r.status === 400 || r.status === 413, String(bad).slice(0, 30));
    }
    assert.equal(sqlite.prepare("SELECT count(*) n FROM app_setting WHERE key='avatar'").get().n, 0);
  } finally { sqlite.close(); }
});
