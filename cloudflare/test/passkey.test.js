// Passkey sign-up, sign-in and management, end to end through the real
// @simplewebauthn/server verification. A software authenticator below builds
// the same responses a browser returns (ES256 key, "none" attestation).
import {DatabaseSync} from 'node:sqlite';
import {readFileSync, readdirSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {encodeCBOR} from '@levischuck/tiny-cbor';
import worker from '../src/worker.js';

const ORIGIN = 'https://taguri.example';
const enc = new TextEncoder();
const b64 = bytes => Buffer.from(bytes).toString('base64url');
const sha256 = async bytes => new Uint8Array(await crypto.subtle.digest('SHA-256', bytes));
const concat = (...parts) => { const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0)); let o = 0; for (const p of parts) { out.set(p, o); o += p.length; } return out; };
const u32 = n => new Uint8Array([n >>> 24, (n >>> 16) & 255, (n >>> 8) & 255, n & 255]);
// WebCrypto gives raw r||s; WebAuthn ES256 signatures are DER.
function der(raw) {
  const int = b => { let i = 0; while (i < b.length - 1 && b[i] === 0) i++; b = b.slice(i); return b[0] & 0x80 ? concat(new Uint8Array([0]), b) : b; };
  const r = int(raw.slice(0, 32)), s = int(raw.slice(32));
  return concat(new Uint8Array([0x30, r.length + s.length + 4, 0x02, r.length]), r, new Uint8Array([0x02, s.length]), s);
}

class SoftAuthenticator {
  constructor() { this.keys = new Map(); }
  async create(options, {origin = ORIGIN, rpId = options.rp.id, uv = true} = {}) {
    const pair = await crypto.subtle.generateKey({name: 'ECDSA', namedCurve: 'P-256'}, true, ['sign', 'verify']);
    const jwk = await crypto.subtle.exportKey('jwk', pair.publicKey);
    const id = crypto.getRandomValues(new Uint8Array(16));
    const cose = encodeCBOR(new Map([[1, 2], [3, -7], [-1, 1], [-2, Buffer.from(jwk.x, 'base64url')], [-3, Buffer.from(jwk.y, 'base64url')]]));
    const authData = concat(await sha256(enc.encode(rpId)), new Uint8Array([0x41 | (uv ? 0x04 : 0)]), u32(0),
      new Uint8Array(16), new Uint8Array([0, id.length]), id, cose);
    const clientData = enc.encode(JSON.stringify({type: 'webauthn.create', challenge: options.challenge, origin, crossOrigin: false}));
    this.keys.set(b64(id), {pair, counter: 0, userHandle: options.user.id});
    return {id: b64(id), rawId: b64(id), type: 'public-key', clientExtensionResults: {}, authenticatorAttachment: 'platform',
      response: {clientDataJSON: b64(clientData), attestationObject: b64(encodeCBOR(new Map([['fmt', 'none'], ['attStmt', new Map()], ['authData', authData]]))), transports: ['internal']}};
  }
  async get(options, id, {origin = ORIGIN, rpId = options.rpId, uv = true, counter, pair, userHandle} = {}) {
    const key = this.keys.get(id);
    key.counter = counter ?? key.counter + 1;
    const authData = concat(await sha256(enc.encode(rpId)), new Uint8Array([0x01 | (uv ? 0x04 : 0)]), u32(key.counter));
    const clientData = enc.encode(JSON.stringify({type: 'webauthn.get', challenge: options.challenge, origin, crossOrigin: false}));
    const sig = new Uint8Array(await crypto.subtle.sign({name: 'ECDSA', hash: 'SHA-256'}, (pair ?? key.pair).privateKey, concat(authData, await sha256(clientData))));
    return {id, rawId: id, type: 'public-key', clientExtensionResults: {},
      response: {clientDataJSON: b64(clientData), authenticatorData: b64(authData), signature: b64(der(sig)), userHandle: userHandle ?? key.userHandle}};
  }
}

function setup() {
  const sqlite = new DatabaseSync(':memory:');
  for (const f of readdirSync(new URL('../migrations/', import.meta.url)).filter(n => n.endsWith('.sql')).sort()) sqlite.exec(readFileSync(new URL(`../migrations/${f}`, import.meta.url), 'utf8'));
  sqlite.exec('PRAGMA foreign_keys = ON');
  const wrap = (sql, args = []) => ({bind(...v) { return wrap(sql, v); }, async first() { return sqlite.prepare(sql).get(...args) ?? null; }, async all() { return {results: sqlite.prepare(sql).all(...args)}; }, async run() { return sqlite.prepare(sql).run(...args); }, async execute() { return /^SELECT/.test(sql) ? this.all() : this.run(); }});
  const env = {ALLOW_REGISTRATION: 'true', DB: {prepare: sql => wrap(sql), async batch(cs) { sqlite.exec('BEGIN'); try { const r = []; for (const c of cs) r.push(await c.execute()); sqlite.exec('COMMIT'); return r; } catch (e) { sqlite.exec('ROLLBACK'); throw e; } }}, ASSETS: {fetch: () => new Response('static')}};
  const call = (path, value, cookie = '', origin = ORIGIN) => worker.fetch(new Request(`${ORIGIN}/api/${path}`, {method: value === undefined ? 'GET' : 'POST', headers: {cookie, origin, 'content-type': 'application/json'}, body: value === undefined ? undefined : JSON.stringify(value)}), env);
  return {call, sqlite, env};
}
const cookieOf = r => r.headers.get('set-cookie')?.split(';')[0] ?? '';
async function signUp(call, auth, cookie = '') {
  const {challenge_id, options} = await (await call('auth/passkey/register/options', {}, cookie)).json();
  const response = await auth.create(options);
  const r = await call('auth/passkey/register/verify', {challenge_id, response}, cookie);
  return {r, status: r.status, body: await r.json(), cookie: cookieOf(r), id: response.id};
}
async function signIn(call, auth, id, opts = {}, cookie = '') {
  const {challenge_id, options} = await (await call('auth/passkey/login/options', {}, cookie)).json();
  const response = await auth.get(options, id, opts);
  const r = await call('auth/passkey/login/verify', {challenge_id, response}, cookie);
  return {status: r.status, body: await r.json(), cookie: cookieOf(r), challenge_id, response};
}

test('sign up with a passkey alone, then sign back in on a fresh browser', async () => {
  const {call, sqlite} = setup();
  const auth = new SoftAuthenticator();
  const up = await signUp(call, auth);
  assert.equal(up.status, 200, JSON.stringify(up.body));
  assert.equal(up.body.created, true);
  assert.match(up.body.recovery_code, /^[a-f0-9]{64}$/);           // backup for a lost device, shown once
  for (const flag of ['HttpOnly', 'Secure', 'SameSite=Lax']) assert.ok(up.r.headers.get('set-cookie').includes(flag));
  await call('record', {id: 'r1', title: '舞台', date: '2026-10-01', rating: '◎'}, up.cookie);
  const back = await signIn(call, auth, up.id);
  assert.equal(back.status, 200, JSON.stringify(back.body));
  assert.equal((await (await call('state', undefined, back.cookie)).json()).records[0].id, 'r1');
  // The recovery code reaches the same account too.
  assert.equal((await call('recover', {code: up.body.recovery_code})).status, 200);
  // Only public material is stored; the counter moved forward.
  const row = sqlite.prepare('SELECT * FROM passkeys').get();
  assert.equal(row.counter, 1);
  assert.ok(row.last_used_at);
  assert.equal(sqlite.prepare('SELECT count(*) AS n FROM users').get().n, 1);
});

test('a signed-in account (e.g. recovery code) can add a passkey and keeps its records', async () => {
  const {call, sqlite} = setup();
  const reg = await call('register', {});
  const cookie = cookieOf(reg);
  await call('record', {id: 'old', title: '前からの記録', date: '2026-09-01'}, cookie);
  const auth = new SoftAuthenticator();
  const add = await signUp(call, auth, cookie);
  assert.deepEqual(add.body, {added: true});
  assert.equal(sqlite.prepare('SELECT count(*) AS n FROM users').get().n, 1);
  const back = await signIn(call, auth, add.id);
  assert.equal((await (await call('state', undefined, back.cookie)).json()).records[0].id, 'old');
  // A second passkey on another device joins the same account and handle.
  const phone = new SoftAuthenticator();
  const opts = await (await call('auth/passkey/register/options', {}, back.cookie)).json();
  assert.deepEqual(opts.options.excludeCredentials.map(c => c.id), [add.id]);      // no duplicate registration
  const r2 = await call('auth/passkey/register/verify', {challenge_id: opts.challenge_id, response: await phone.create(opts.options)}, back.cookie);
  assert.equal(r2.status, 200);
  assert.equal(sqlite.prepare('SELECT count(DISTINCT user_handle) AS n FROM passkeys').get().n, 1);
  const listed = await (await call('auth/passkeys', undefined, back.cookie)).json();
  assert.equal(listed.passkeys.length, 2);
  assert.ok(listed.passkeys.every(p => !('public_key' in p)));
});

test('adding a passkey to an account needs a sign-in within 10 minutes', async () => {
  const {call, sqlite} = setup();
  const cookie = cookieOf(await call('register', {}));
  sqlite.prepare('UPDATE sessions SET created_at=created_at-601').run();
  const r = await call('auth/passkey/register/options', {}, cookie);
  assert.equal(r.status, 401);
  assert.match((await r.json()).error, /10分以内/);
  // A challenge taken while fresh cannot be finished once the sign-in is old.
  sqlite.prepare('UPDATE sessions SET created_at=?').run(Math.floor(Date.now() / 1000));
  const {challenge_id, options} = await (await call('auth/passkey/register/options', {}, cookie)).json();
  sqlite.prepare('UPDATE sessions SET created_at=created_at-601').run();
  const v = await call('auth/passkey/register/verify', {challenge_id, response: await new SoftAuthenticator().create(options)}, cookie);
  assert.equal(v.status, 401);
  assert.equal(sqlite.prepare('SELECT count(*) AS n FROM passkeys').get().n, 0);
});

test('forged, replayed, cloned or foreign responses are rejected', async () => {
  const {call, sqlite} = setup();
  const auth = new SoftAuthenticator();
  const up = await signUp(call, auth);
  const stranger = await crypto.subtle.generateKey({name: 'ECDSA', namedCurve: 'P-256'}, true, ['sign', 'verify']);
  const cases = {
    'wrong origin (phishing site)': {origin: 'https://evil.example'},
    'wrong RP ID': {rpId: 'evil.example'},
    'no user verification': {uv: false},
    'signed by another key': {pair: stranger},
    'different user handle': {userHandle: b64(new Uint8Array(32))},
  };
  for (const [name, opts] of Object.entries(cases)) assert.equal((await signIn(call, auth, up.id, opts)).status, 401, name);
  // A used challenge cannot be reused, even with a valid response.
  const ok = await signIn(call, auth, up.id);
  assert.equal(ok.status, 200);
  // Once the stored counter has moved, a response that does not advance it
  // means a cloned key. (0 and 0 is allowed by the spec: no counter.)
  const stored = sqlite.prepare('SELECT counter FROM passkeys').get().counter;
  assert.ok(stored > 0);
  assert.equal((await signIn(call, auth, up.id, {counter: stored})).status, 401, 'counter not advanced (cloned key)');
  const replay = await call('auth/passkey/login/verify', {challenge_id: ok.challenge_id, response: ok.response});
  assert.equal(replay.status, 400);
  // Expired challenge.
  const {challenge_id, options} = await (await call('auth/passkey/login/options', {})).json();
  sqlite.prepare('UPDATE webauthn_challenges SET expires_at=0').run();
  assert.equal((await call('auth/passkey/login/verify', {challenge_id, response: await auth.get(options, up.id)})).status, 400);
  // Unknown credential and malformed input.
  const other = new SoftAuthenticator();
  const lone = await (await call('auth/passkey/register/options', {})).json();
  const unknown = await other.create(lone.options);                       // never verified, so not stored
  const opt2 = await (await call('auth/passkey/login/options', {})).json();
  assert.equal((await call('auth/passkey/login/verify', {challenge_id: opt2.challenge_id, response: await other.get(opt2.options, unknown.id)})).status, 401);
  assert.equal((await call('auth/passkey/login/verify', {challenge_id: 'x', response: {}})).status, 400);
  // Registration with a tampered origin is refused and stores nothing.
  const reg = await (await call('auth/passkey/register/options', {})).json();
  const bad = await call('auth/passkey/register/verify', {challenge_id: reg.challenge_id, response: await new SoftAuthenticator().create(reg.options, {origin: 'https://evil.example'})});
  assert.equal(bad.status, 401);
  const noUv = await (await call('auth/passkey/register/options', {})).json();
  assert.equal((await call('auth/passkey/register/verify', {challenge_id: noUv.challenge_id, response: await new SoftAuthenticator().create(noUv.options, {uv: false})})).status, 401);
  assert.equal(sqlite.prepare('SELECT count(*) AS n FROM passkeys').get().n, 1);
});

test('a challenge to add a passkey cannot be completed by someone else or after sign-out', async () => {
  const {call, sqlite} = setup();
  const a = cookieOf(await call('register', {})), b = cookieOf(await call('register', {}));
  const auth = new SoftAuthenticator();
  const {challenge_id, options} = await (await call('auth/passkey/register/options', {}, a)).json();
  const response = await auth.create(options);
  assert.equal((await call('auth/passkey/register/verify', {challenge_id, response}, b)).status, 401);      // other account
  const again = await (await call('auth/passkey/register/options', {}, a)).json();
  assert.equal((await call('auth/passkey/register/verify', {challenge_id: again.challenge_id, response: await auth.create(again.options)}, '')).status, 401);   // signed out
  assert.equal(sqlite.prepare('SELECT count(*) AS n FROM passkeys').get().n, 0);
  assert.equal(sqlite.prepare('SELECT count(*) AS n FROM users').get().n, 2);
});

test('closed registration still lets members add passkeys; deleting a passkey stops it; scoped to the owner', async () => {
  const {call, env} = setup();
  const auth = new SoftAuthenticator();
  const up = await signUp(call, auth);
  env.ALLOW_REGISTRATION = 'false';
  assert.equal((await call('auth/passkey/register/options', {})).status, 503);
  assert.equal((await signUp(call, new SoftAuthenticator(), up.cookie)).status, 200);
  const other = cookieOf(await (async () => { env.ALLOW_REGISTRATION = 'true'; return call('register', {}); })());
  await call('auth/passkeys/delete', {id: up.id}, other);                   // someone else's: no effect
  assert.equal((await signIn(call, auth, up.id)).status, 200);
  await call('auth/passkeys/delete', {id: up.id}, up.cookie);
  assert.equal((await signIn(call, auth, up.id)).status, 401);
  assert.equal((await call('auth/passkeys', undefined, '')).status, 401);
});

test('cross-origin requests are refused and pending challenges are bounded', async () => {
  const {call, sqlite} = setup();
  assert.equal((await call('auth/passkey/login/options', {}, '', 'https://evil.example')).status, 403);
  const insert = sqlite.prepare('INSERT INTO webauthn_challenges(id,challenge,purpose,expires_at) VALUES(?,?,?,?)');
  for (let i = 0; i < 1000; i++) insert.run(String(i), 'c', 'login', Math.floor(Date.now() / 1000) + 300);
  assert.equal((await call('auth/passkey/login/options', {})).status, 429);
  sqlite.prepare('UPDATE webauthn_challenges SET expires_at=0').run();       // expired ones are swept
  assert.equal((await call('auth/passkey/login/options', {})).status, 200);
});
