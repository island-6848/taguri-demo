// Signed-out visitors see only /login and /about; everything else asks them
// to sign in. Signed-in users get the app as before.
import {DatabaseSync} from 'node:sqlite';
import {readFileSync, readdirSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import worker, {safeNext} from '../src/worker.js';

const ORIGIN = 'https://taguri.example';
function setup() {
  const sqlite = new DatabaseSync(':memory:');
  for (const f of readdirSync(new URL('../migrations/', import.meta.url)).filter(n => n.endsWith('.sql')).sort()) sqlite.exec(readFileSync(new URL(`../migrations/${f}`, import.meta.url), 'utf8'));
  const wrap = (sql, args = []) => ({bind(...v) { return wrap(sql, v); }, async first() { return sqlite.prepare(sql).get(...args) ?? null; }, async all() { return {results: sqlite.prepare(sql).all(...args)}; }, async run() { return sqlite.prepare(sql).run(...args); }, async execute() { return /^SELECT/.test(sql) ? this.all() : this.run(); }});
  const served = [];
  const env = {ALLOW_REGISTRATION: 'true', ORIGINAL_UI_BRIDGE: 'true',
    DB: {prepare: sql => wrap(sql), async batch(cs) { sqlite.exec('BEGIN'); try { const r = []; for (const c of cs) r.push(await c.execute()); sqlite.exec('COMMIT'); return r; } catch (e) { sqlite.exec('ROLLBACK'); throw e; } }},
    ASSETS: {fetch: async req => { served.push(new URL(req.url).pathname); return new Response('<nav class="side"></nav>', {headers: {'content-type': 'text/html'}}); }}};
  const get = (path, cookie = '') => worker.fetch(new Request(ORIGIN + path, {headers: {cookie}}), env);
  const post = (path, value, cookie = '') => worker.fetch(new Request(ORIGIN + path, {method: 'POST', headers: {cookie, origin: ORIGIN, 'content-type': 'application/json'}, body: JSON.stringify(value)}), env);
  return {get, post, served, env};
}

test('signed out: the top goes to /about, other pages to /login with a way back', async () => {
  const {get, served} = setup();
  const top = await get('/');
  assert.equal(top.status, 302);
  assert.equal(top.headers.get('location'), '/about');
  for (const path of ['/recommend', '/settings?tab=1', '/migration-data/', '/records/works', '/anything']) {
    const r = await get(path);
    assert.equal(r.status, 302, path);
    assert.equal(r.headers.get('location'), '/login?next=' + encodeURIComponent(path));
  }
  assert.deepEqual(served, [], 'no app page was served');
});

test('signed out: /login, /about and static files load; app data and posters do not', async () => {
  const {get, post, served} = setup();
  for (const path of ['/login', '/about', '/style.css', '/auth.css', '/vendor/firebase-login.js', '/assets/taguri-howto.mp4']) {
    const r = await get(path);
    assert.equal(r.status, 200, path);
  }
  assert.deepEqual(served, ['/login', '/about', '/style.css', '/auth.css', '/vendor/firebase-login.js', '/assets/taguri-howto.mp4']);
  for (const path of ['/api/screen/recommend', '/img/poster.jpg', '/migration-api/state']) assert.equal((await get(path)).status, 401, path);
  assert.equal((await post('/api/react', {stage_id: 's', value: 1})).status, 401);
  // Sign-in itself stays reachable.
  assert.notEqual((await get('/api/auth/config')).status, 401);
  assert.equal((await post('/api/auth/passkey/login/options', {})).status, 200);
});

test('signed in: pages are served (with the account link) and expired sessions are sent back', async () => {
  const {get, post, served} = setup();
  const reg = await post('/migration-api/register', {});
  const cookie = reg.headers.get('set-cookie').split(';')[0];
  const page = await get('/recommend', cookie);
  assert.equal(page.status, 200);
  assert.ok(served.includes('/recommend'));
  assert.equal((await get('/migration-data/', cookie)).status, 200);
  assert.equal((await get('/', cookie)).status, 200);
  assert.equal((await get('/recommend', 'taguri_session=' + 'a'.repeat(64))).status, 302);   // unknown session
});

test('the return path after sign-in stays on this site', () => {
  assert.equal(safeNext('/recommend?pref=東京'), '/recommend?pref=東京');
  for (const bad of ['//evil.example', '/\\evil.example', 'https://evil.example', 'javascript:alert(1)', '/login?next=/x', '', null, undefined, 42]) assert.equal(safeNext(bad), '/', String(bad));
});
