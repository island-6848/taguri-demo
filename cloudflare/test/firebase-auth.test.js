import {DatabaseSync} from 'node:sqlite';
import {readFileSync, readdirSync} from 'node:fs';
import {test, beforeEach} from 'node:test';
import assert from 'node:assert/strict';
import worker from '../src/worker.js';
import {JWKS_URL, MAX_AUTH_AGE, resetKeyCache, verifyIdToken} from '../src/firebase-auth.js';

const PROJECT = 'taguri-test';
const enc = new TextEncoder();
const b64 = bytes => Buffer.from(bytes).toString('base64url');
const keyPair = () => crypto.subtle.generateKey({name: 'RSASSA-PKCS1-v1_5', modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]), hash: 'SHA-256'}, true, ['sign', 'verify']);
const google = await keyPair(), stranger = await keyPair();
let jwksFetches = 0;
async function publishKeys(...pairs) {
  const keys = [];
  for (const [kid, pair] of pairs) keys.push({...(await crypto.subtle.exportKey('jwk', pair.publicKey)), kid, alg: 'RS256', use: 'sig'});
  globalThis.fetch = async url => {
    assert.equal(String(url), JWKS_URL);           // never any other host
    jwksFetches++;
    return Response.json({keys}, {headers: {'cache-control': 'public, max-age=3600'}});
  };
}
const nowSec = () => Math.floor(Date.now() / 1000);
async function idToken(claims = {}, {kid = 'k1', pair = google, alg = 'RS256', header = {}} = {}) {
  const t = nowSec();
  const payload = {iss: `https://securetoken.google.com/${PROJECT}`, aud: PROJECT, sub: 'firebase-user-1', iat: t, exp: t + 3600, auth_time: t,
    email: 'someone@example.com', email_verified: true, firebase: {sign_in_provider: 'google.com'}, ...claims};
  const head = b64(enc.encode(JSON.stringify({alg, kid, typ: 'JWT', ...header})));
  const body = b64(enc.encode(JSON.stringify(payload)));
  const sig = await crypto.subtle.sign('RSASSA-PKCS1-v1_5', pair.privateKey, enc.encode(`${head}.${body}`));
  return `${head}.${body}.${b64(sig)}`;
}

function setup() {
  const sqlite = new DatabaseSync(':memory:');
  for (const file of readdirSync(new URL('../migrations/', import.meta.url)).filter(n => n.endsWith('.sql')).sort()) sqlite.exec(readFileSync(new URL(`../migrations/${file}`, import.meta.url), 'utf8'));
  const wrap = (sql, args = []) => ({bind(...values) { return wrap(sql, values); }, async first() { return sqlite.prepare(sql).get(...args) ?? null; }, async all() { return {results: sqlite.prepare(sql).all(...args)}; }, async run() { return sqlite.prepare(sql).run(...args); }, async execute() { return /^SELECT/.test(sql) ? this.all() : this.run(); }});
  const env = {ALLOW_REGISTRATION: 'true', FIREBASE_PROJECT_ID: PROJECT, DB: {prepare: sql => wrap(sql), async batch(commands) { sqlite.exec('BEGIN'); try { const result = []; for (const c of commands) result.push(await c.execute()); sqlite.exec('COMMIT'); return result; } catch (e) { sqlite.exec('ROLLBACK'); throw e; } }}, ASSETS: {fetch: () => new Response('static')}};
  const call = (path, value, cookie = '', origin = 'https://taguri.example') => worker.fetch(new Request(`https://taguri.example/api/${path}`, {method: value === undefined ? 'GET' : 'POST', headers: {cookie, origin, 'content-type': 'application/json'}, body: value === undefined ? undefined : JSON.stringify(value)}), env);
  return {call, sqlite, env};
}
const cookieOf = response => response.headers.get('set-cookie').split(';')[0];
async function signIn(call, token, cookie = '', extra = {}) {
  const response = await call('auth/firebase', {id_token: token, ...extra}, cookie);
  return {response, status: response.status, cookie: response.status === 200 ? cookieOf(response) : '', body: await response.json()};
}

beforeEach(async () => { resetKeyCache(); jwksFetches = 0; await publishKeys(['k1', google]); });

test('a Google sign-in creates one account and signs back into it; only the UID is stored', async () => {
  const {call, sqlite} = setup();
  const first = await signIn(call, await idToken());
  assert.equal(first.status, 200);
  assert.deepEqual(first.body, {linked: false, created: true});
  assert.match(first.cookie, /^taguri_session=[a-f0-9]{64}$/);
  const set = first.response.headers.get('set-cookie');
  for (const flag of ['HttpOnly', 'Secure', 'SameSite=Strict']) assert.ok(set.includes(flag), flag);
  await call('record', {id: 'r1', title: '舞台', date: '2026-10-01', rating: '◎'}, first.cookie);
  const again = await signIn(call, await idToken());
  assert.deepEqual(again.body, {linked: false, created: false});
  assert.equal((await (await call('state', undefined, again.cookie)).json()).records[0].title, '舞台');
  assert.equal(sqlite.prepare('SELECT count(*) AS n FROM users').get().n, 1);
  // No email, name or token is persisted anywhere in D1.
  const dump = JSON.stringify(['users', 'sessions'].map(t => sqlite.prepare(`SELECT * FROM ${t}`).all()));
  assert.ok(!dump.includes('someone@example.com'));
  assert.ok(!dump.includes(first.cookie.split('=')[1]));
  // Accounts made by Firebase sign-in cannot be reached with any recovery code.
  assert.match(sqlite.prepare('SELECT recovery_hash FROM users').get().recovery_hash, /^firebase:/);
});

test('a recovery-code account is linked only when asked from the account page, and keeps its records', async () => {
  const {call, sqlite} = setup();
  const reg = await call('register', {});
  const anon = cookieOf(reg), {recovery_code} = await reg.json();
  await call('record', {id: 'old', title: '前からの記録', date: '2026-09-01'}, anon);
  // A plain sign-in on a device where someone's unlinked account is open
  // neither links it nor silently starts another account.
  const plain = await signIn(call, await idToken(), anon);
  assert.equal(plain.status, 409);
  assert.equal(sqlite.prepare('SELECT count(*) AS n FROM users WHERE firebase_uid IS NOT NULL').get().n, 0);
  const linked = await signIn(call, await idToken(), anon, {link: true});
  assert.deepEqual(linked.body, {linked: true, created: false});
  // The pre-login session is revoked (session rotation).
  assert.equal((await call('state', undefined, anon)).status, 401);
  // A fresh device signing in with the same Google account sees the same records.
  const other = await signIn(call, await idToken());
  assert.equal((await (await call('state', undefined, other.cookie)).json()).records[0].id, 'old');
  // The recovery code still works for the linked account.
  assert.equal((await call('recover', {code: recovery_code})).status, 200);
  assert.equal(sqlite.prepare('SELECT count(*) AS n FROM users').get().n, 1);
});

test('linking needs a sign-in within 10 minutes and a Google account not used elsewhere', async () => {
  const {call, sqlite} = setup();
  assert.equal((await signIn(call, await idToken(), '', {link: true})).status, 401);       // nobody signed in
  const anon = cookieOf(await call('register', {}));
  sqlite.prepare('UPDATE sessions SET created_at=created_at-601').run();
  const stale = await signIn(call, await idToken(), anon, {link: true});
  assert.equal(stale.status, 401);
  assert.match(stale.body.error, /10分以内/);
  assert.equal(sqlite.prepare('SELECT count(*) AS n FROM users WHERE firebase_uid IS NOT NULL').get().n, 0);
  // Google already belongs to another account: refused, not switched to it.
  await signIn(call, await idToken({sub: 'firebase-user-2'}));
  const fresh = cookieOf(await call('register', {}));
  const taken = await signIn(call, await idToken({sub: 'firebase-user-2'}), fresh, {link: true});
  assert.equal(taken.status, 409);
  assert.equal((await call('state', undefined, fresh)).status, 200);                    // still signed in as before
});

test('two existing accounts are never merged', async () => {
  const {call, sqlite} = setup();
  const a = await signIn(call, await idToken());
  await call('record', {id: 'a', title: 'Aの記録', date: '2026-09-01'}, a.cookie);
  const reg = await call('register', {});
  const b = cookieOf(reg);
  await call('record', {id: 'b', title: 'Bの記録', date: '2026-09-02'}, b);
  const now = await signIn(call, await idToken(), b);        // same Google account as A
  assert.deepEqual(now.body, {linked: false, created: false});
  assert.deepEqual((await (await call('state', undefined, now.cookie)).json()).records.map(r => r.id), ['a']);
  assert.equal(sqlite.prepare("SELECT count(*) AS n FROM records WHERE id='b'").get().n, 1);
  assert.equal(sqlite.prepare('SELECT count(*) AS n FROM users WHERE firebase_uid IS NOT NULL').get().n, 1);
});

test('forged, expired, foreign or unsupported tokens are rejected without creating accounts', async () => {
  const {call, sqlite} = setup();
  const t = nowSec();
  const tampered = (await idToken()).split('.');
  tampered[1] = b64(enc.encode(JSON.stringify({...JSON.parse(Buffer.from(tampered[1], 'base64url')), sub: 'someone-else'})));
  const cases = {
    'wrong audience': await idToken({aud: 'other-project'}),
    'wrong issuer': await idToken({iss: 'https://securetoken.google.com/other-project'}),
    'expired': await idToken({exp: t - 120, iat: t - 3720, auth_time: t - 3720}),
    'issued in the future': await idToken({iat: t + 600}),
    'old sign-in replayed': await idToken({auth_time: t - MAX_AUTH_AGE - 120}),
    'empty subject': await idToken({sub: ''}),
    'anonymous provider': await idToken({firebase: {sign_in_provider: 'anonymous'}}),
    'custom token provider': await idToken({firebase: {sign_in_provider: 'custom'}}),
    'unverified email/password': await idToken({email_verified: false, firebase: {sign_in_provider: 'password'}}),
    'signed by another key': await idToken({}, {pair: stranger}),
    'unknown key id': await idToken({}, {kid: 'nope'}),
    'HS256 header': await idToken({}, {alg: 'HS256'}),
    'tampered payload': tampered.join('.'),
    'unsigned': (await idToken()).split('.').slice(0, 2).join('.') + '.',
    'not a JWT': 'abc',
    'oversized': 'a'.repeat(5000),
  };
  for (const [name, token] of Object.entries(cases)) assert.equal((await signIn(call, token)).status, 401, name);
  assert.equal((await signIn(call, 12345)).status, 401, 'non-string');
  assert.equal(sqlite.prepare('SELECT count(*) AS n FROM users').get().n, 0);
  // A verified email-link sign-in (reported as "password") is accepted.
  assert.equal((await signIn(call, await idToken({firebase: {sign_in_provider: 'password'}}))).status, 200);
});

test('cross-origin requests, missing configuration and closed registration fail safely', async () => {
  const {call, env} = setup();
  const token = await idToken();
  assert.equal((await call('auth/firebase', {id_token: token}, '', 'https://evil.example')).status, 403);
  delete env.FIREBASE_PROJECT_ID;
  assert.equal((await signIn(call, token)).status, 503);
  env.FIREBASE_PROJECT_ID = PROJECT; env.ALLOW_REGISTRATION = 'false';
  assert.equal((await signIn(call, token)).status, 503);
});

test('Google keys are cached, and unknown key ids cannot force repeated fetches', async () => {
  const {call} = setup();
  for (let i = 0; i < 3; i++) assert.equal((await signIn(call, await idToken({sub: `u${i}`}))).status, 200);
  assert.equal(jwksFetches, 1);
  for (let i = 0; i < 5; i++) assert.equal((await signIn(call, await idToken({}, {kid: `bogus${i}`}))).status, 401);
  assert.ok(jwksFetches <= 2, `fetched ${jwksFetches} times`);
});

test('key rotation: a token signed with a newly published key is accepted after refetch', async () => {
  const rotated = await keyPair();
  assert.equal((await verifyIdToken(await idToken(), PROJECT)).uid, 'firebase-user-1');
  await publishKeys(['k1', google], ['k2', rotated]);
  // Within the refetch interval an unknown kid is not refetched...
  await assert.rejects(verifyIdToken(await idToken({}, {kid: 'k2', pair: rotated}), PROJECT));
  // ...but after it, the new key is picked up.
  assert.equal((await verifyIdToken(await idToken({}, {kid: 'k2', pair: rotated}), PROJECT, nowSec() + 61)).uid, 'firebase-user-1');
});

test('sign out of all devices revokes every session of the account only', async () => {
  const {call} = setup();
  const one = await signIn(call, await idToken()), two = await signIn(call, await idToken());
  const other = await signIn(call, await idToken({sub: 'someone-else'}));
  assert.equal((await call('logout/all', {}, one.cookie)).status, 200);
  assert.equal((await call('state', undefined, one.cookie)).status, 401);
  assert.equal((await call('state', undefined, two.cookie)).status, 401);
  assert.equal((await call('state', undefined, other.cookie)).status, 200);
});

test('signing in with a different Google account while signed in never lands in the current account', async () => {
  const {call, sqlite} = setup();
  const x = await signIn(call, await idToken({sub: 'google-x'}));
  await call('record', {id: 'x', title: 'Xの記録', date: '2026-09-01'}, x.cookie);
  const y = await signIn(call, await idToken({sub: 'google-y'}), x.cookie);
  assert.deepEqual(y.body, {linked: false, created: true});
  assert.equal((await (await call('state', undefined, y.cookie)).json()).records.length, 0);
  assert.equal(sqlite.prepare("SELECT firebase_uid FROM users WHERE id=(SELECT user_id FROM records WHERE id='x')").get().firebase_uid, 'google-x');
});

test('login page has its own narrow policy; config is public and auth is never bridged to Render', async () => {
  const {env} = setup();
  // Like Workers static assets: /login.html redirects to /login, which serves the file.
  env.ASSETS = {fetch: async req => new URL(req.url).pathname === '/login'
    ? new Response('<!doctype html>login', {headers: {'content-type': 'text/html', 'Content-Security-Policy': "default-src 'self'"}})
    : new Response(null, {status: 307, headers: {location: '/login'}})};
  env.ORIGINAL_UI_BRIDGE = 'true';
  const get = path => worker.fetch(new Request(`https://taguri.example${path}`), env);
  // No API key yet: the page still loads, config says not ready.
  assert.equal((await get('/api/auth/config')).status, 503);
  env.FIREBASE_API_KEY = 'public-web-key';
  const config = await (await get('/api/auth/config')).json();
  assert.deepEqual(config, {apiKey: 'public-web-key', projectId: PROJECT, authDomain: `${PROJECT}.firebaseapp.com`, calendarClientId: ''});
  const page = await get('/login');
  assert.equal(page.status, 200);
  const csp = page.headers.get('content-security-policy');
  assert.match(csp, /script-src 'self' https:\/\/apis\.google\.com(;|$)/);
  assert.match(csp, new RegExp(`frame-src https://${PROJECT}\\.firebaseapp\\.com(;|$)`));
  assert.match(csp, /frame-ancestors 'none'/);
  assert.ok(!csp.includes('recaptcha') && !csp.includes('unsafe-'), csp);
  assert.equal(page.headers.get('cache-control'), 'no-store');
  // With the Render bridge on, sign-in still reaches this Worker.
  const signed = await worker.fetch(new Request('https://taguri.example/api/auth/firebase', {method: 'POST', headers: {origin: 'https://taguri.example', 'content-type': 'application/json'}, body: JSON.stringify({id_token: await idToken()})}), env);
  assert.equal(signed.status, 200);
});
