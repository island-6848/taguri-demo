// システムテスト SC-11-01・SC-04-02・EN-05-01（docs/system-test-spec.md）: 応答のセキュリティのヘッダと
// キャッシュの指定が、決めたとおりで弱まっていない。
// - 静的な画面は Cloudflare が public/_headers を付ける（Worker を通らない）ので、ファイルそのものを読む
// - Worker が答えるもの（ログイン・API・書き出し・ポスター・思わぬ失敗）は、Worker の応答を見る
// 元の画面の CSP の 'unsafe-inline'・'unsafe-eval' は分かっている穴（q-original-ui-csp）。ここでは今より
// 広げないこと（許すものが増えないこと）を見る。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import worker, {troubleResponse} from '../src/worker.js';
import {setup, signIn} from './screens/harness.js';

const ORIGIN = 'https://taguri.example';
const csp = value => Object.fromEntries(String(value || '').split(';').map(s => s.trim()).filter(Boolean).map(s => { const [k, ...v] = s.split(/\s+/); return [k, v]; }));

function staticHeaders() {
  const out = {}; let path = null;
  for (const line of readFileSync(new URL('../public/_headers', import.meta.url), 'utf8').split('\n')) {
    if (!line.trim() || line.trim().startsWith('#')) continue;
    if (!/^\s/.test(line)) { path = line.trim(); out[path] = {}; continue; }
    const i = line.indexOf(':'); out[path][line.slice(0, i).trim().toLowerCase()] = line.slice(i + 1).trim();
  }
  return out;
}

test('SC-11-01: 静的な画面（public/_headers の /*）のヘッダ', () => {
  const all = staticHeaders()['/*'];
  assert.ok(all, '/* の指定がある');
  assert.equal(all['x-content-type-options'], 'nosniff');
  assert.equal(all['x-frame-options'], 'DENY');
  assert.equal(all['referrer-policy'], 'no-referrer');
  const p = csp(all['content-security-policy']);
  assert.deepEqual(p['default-src'], ["'self'"]);
  assert.deepEqual(p['frame-ancestors'], ["'none'"]);
  assert.deepEqual(p['base-uri'], ["'none'"]);
  assert.deepEqual(p['connect-src'], ["'self'"], '画面から外へ通信しない');
  // 今より広げない（q-original-ui-csp の結論が出たら、ここを狭める）
  const allowed = {'script-src': ["'self'", "'unsafe-inline'", "'unsafe-eval'"], 'style-src': ["'self'", "'unsafe-inline'"], 'img-src': ["'self'", 'data:'], 'form-action': ["'self'"]};
  for (const [k, ok] of Object.entries(allowed)) for (const v of p[k] || []) assert.ok(ok.includes(v), `${k} に ${v} が増えた`);
  for (const [k, vs] of Object.entries(p)) for (const v of vs) assert.ok(!/^(\*|https?:|http:)$/.test(v) && !v.startsWith('http:'), `${k} に ${v}`);
});

test('SC-11-01・SC-04-02: ログインの画面（Worker が付ける CSP）', async () => {
  const {env} = setup();
  env.ASSETS = {fetch: async () => new Response('<!doctype html><title>login</title>', {headers: {'content-type': 'text/html'}})};
  const r = await worker.fetch(new Request(ORIGIN + '/login'), env);
  assert.equal(r.status, 200);
  assert.equal(r.headers.get('x-content-type-options'), 'nosniff');
  const p = csp(r.headers.get('content-security-policy'));
  assert.deepEqual(p['frame-ancestors'], ["'none'"]);
  assert.deepEqual(p['object-src'], ["'none'"]);
  assert.deepEqual(p['base-uri'], ["'none'"]);
  assert.ok(!p['script-src'].includes("'unsafe-inline'") && !p['script-src'].includes("'unsafe-eval'"), 'ログインの画面は inline のスクリプトを許さない');
});

test('SC-11-01: API・書き出し・思わぬ失敗は nosniff で、本人の中身を置いておかせない', async () => {
  const {env} = setup();
  const a = await signIn(env);
  const get = (path, cookie = a) => worker.fetch(new Request(ORIGIN + path, {headers: {cookie}}), env);
  for (const path of ['/api/screen/rate', '/api/screen/recommend', '/api/screen/account']) {
    const r = await get(path);
    assert.equal(r.status, 200, path);
    assert.equal(r.headers.get('x-content-type-options'), 'nosniff', path);
    assert.match(r.headers.get('cache-control') || '', /no-store/, `${path} は置いておかせない`);
  }
  const health = await get('/api/health', '');
  assert.equal(health.status, 200);
  assert.equal(health.headers.get('x-content-type-options'), 'nosniff');
  assert.match(health.headers.get('cache-control'), /^public, max-age=\d+$/, 'health は誰のものでもないので置いてよい');
  const exported = await get('/export.json');
  if (exported.status === 200) {
    assert.match(exported.headers.get('cache-control'), /no-store/);
    assert.match(exported.headers.get('content-disposition'), /^attachment;/);
  }
  for (const path of ['/api/screen/rate', '/recommend']) {
    const t = troubleResponse(new Request(ORIGIN + path));
    assert.equal(t.status, 503, path);
    assert.equal(t.headers.get('cache-control'), 'no-store', path);
    assert.equal(t.headers.get('x-content-type-options'), 'nosniff', path);
  }
});

test('EN-05-01: ポスターはブラウザに 1 週間置き、ほかの人と分け合う置き場には置かせない', async () => {
  const {env} = setup();
  const a = await signIn(env);
  env.POSTERS = {get: async name => name === 'p1.jpg' ? {body: 'jpg', httpEtag: '"e1"', httpMetadata: {contentType: 'image/jpeg'}} : null};
  const r = await worker.fetch(new Request(ORIGIN + '/img/p1.jpg', {headers: {cookie: a}}), env);
  assert.equal(r.status, 200);
  assert.equal(r.headers.get('cache-control'), 'private, max-age=604800, immutable');
  assert.equal(r.headers.get('x-content-type-options'), 'nosniff');
  const sh = staticHeaders();
  for (const path of ['/sw.js', '/manifest.webmanifest']) assert.equal(sh[path]?.['cache-control'], 'no-cache', `${path} は毎回確かめる`);
});
