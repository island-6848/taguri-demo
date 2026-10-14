// Request limits (src/rate-limit.js): a brake per visitor from the Rate
// Limiting binding, and an exact daily cap on new accounts.
import {DatabaseSync} from 'node:sqlite';
import {readFileSync, readdirSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import worker from '../src/worker.js';
import {limitKind, checkNewAccount} from '../src/rate-limit.js';

const ORIGIN = 'https://taguri.example';
// A stand-in for the binding: exact counts per key, `limit` per window.
const limiter = limit => { const seen = new Map(); return {seen, async limit({key}) { const n = (seen.get(key) || 0) + 1; seen.set(key, n); return {success: n <= limit}; }}; };
function setup(extra = {}) {
  const sqlite = new DatabaseSync(':memory:');
  for (const f of readdirSync(new URL('../migrations/', import.meta.url)).filter(n => n.endsWith('.sql')).sort()) sqlite.exec(readFileSync(new URL(`../migrations/${f}`, import.meta.url), 'utf8'));
  const wrap = (sql, args = []) => ({bind(...v) { return wrap(sql, v); }, async first() { return sqlite.prepare(sql).get(...args) ?? null; }, async all() { return {results: sqlite.prepare(sql).all(...args)}; }, async run() { return sqlite.prepare(sql).run(...args); }, async execute() { return /^SELECT/.test(sql) ? this.all() : this.run(); }});
  const env = {ALLOW_REGISTRATION: 'true', ORIGINAL_UI_BRIDGE: 'false',
    DB: {prepare: sql => wrap(sql), async batch(cs) { sqlite.exec('BEGIN'); try { const r = []; for (const c of cs) r.push(await c.execute()); sqlite.exec('COMMIT'); return r; } catch (e) { sqlite.exec('ROLLBACK'); throw e; } }},
    ASSETS: {fetch: async () => new Response('ok', {headers: {'content-type': 'text/html'}})}, ...extra};
  const post = (path, ip) => worker.fetch(new Request(ORIGIN + path, {method: 'POST', headers: {origin: ORIGIN, 'content-type': 'application/json', 'cf-connecting-ip': ip}, body: '{}'}), env);
  const get = (path, ip) => worker.fetch(new Request(ORIGIN + path, {headers: {'cf-connecting-ip': ip}}), env);
  return {env, post, get, sqlite};
}

test('sign-in, sign-up and recovery are the auth kind; the rest is any', () => {
  for (const p of ['/api/register', '/api/recover', '/migration-api/register', '/api/auth/firebase', '/api/auth/passkey/login/options', '/api/auth/passkey/register/verify'])
    assert.equal(limitKind('POST', p), 'auth', p);
  for (const [m, p] of [['GET', '/api/register'], ['POST', '/api/record'], ['POST', '/api/registerx'], ['GET', '/recommend'], ['POST', '/api/auth/passkeys/delete']])
    assert.equal(limitKind(m, p), 'any', `${m} ${p}`);
});

test('sign-ups over the limit get 429, and one address does not use up another', async () => {
  const {post, env} = setup({RL_AUTH: limiter(3), RL_ANY: limiter(1000)});
  const codes = [];
  for (let i = 0; i < 5; i++) codes.push((await post('/api/register', '198.51.100.1')).status);
  assert.deepEqual(codes, [200, 200, 200, 429, 429]);
  const r = await post('/api/register', '198.51.100.1');
  assert.equal(r.headers.get('retry-after'), '60');
  assert.match((await r.json()).error, /待って/);
  assert.equal((await post('/api/register', '203.0.113.9')).status, 200);
  assert.ok(env.RL_AUTH.seen.has('auth:198.51.100.1') && env.RL_AUTH.seen.has('auth:203.0.113.9'));
});

test('the brake stops a flood before the sign-in check reads D1', async () => {
  let reads = 0;
  const {get, env} = setup({RL_ANY: limiter(2)});
  const prepare = env.DB.prepare; env.DB.prepare = sql => { reads++; return prepare(sql); };
  assert.equal((await get('/recommend', '198.51.100.7')).status, 302);
  assert.equal((await get('/recommend', '198.51.100.7')).status, 302);
  const before = reads;
  const r = await get('/recommend', '198.51.100.7');
  assert.equal(r.status, 429);
  assert.match(r.headers.get('content-type'), /text\/plain/);
  assert.equal(reads, before);
  assert.equal((await get('/api/state', '198.51.100.7')).headers.get('content-type'), 'application/json');
});

test('without the binding, or when it fails, requests pass', async () => {
  assert.equal((await setup().post('/api/register', '198.51.100.1')).status, 200);
  const broken = {async limit() { throw new Error('down'); }};
  assert.equal((await setup({RL_ANY: broken, RL_AUTH: broken}).post('/api/register', '198.51.100.1')).status, 200);
});

test('new accounts stop at the daily cap (JST day) and open again the next day', async () => {
  const {post, sqlite} = setup({NEW_ACCOUNTS_PER_DAY: '2'});
  assert.equal((await post('/api/register', 'a')).status, 200);
  assert.equal((await post('/api/register', 'b')).status, 200);
  const r = await post('/api/register', 'c');
  assert.equal(r.status, 503);
  assert.match((await r.json()).error, /明日/);
  assert.equal(sqlite.prepare('SELECT count(*) AS n FROM users').get().n, 2);
  // Yesterday's (JST) accounts do not count.
  sqlite.exec('UPDATE users SET created_at = created_at - 86400');
  assert.equal((await post('/api/register', 'c')).status, 200);
});

test('the JST day boundary: 23:59 JST counts toward that day, 00:00 JST starts a new one', async () => {
  const rows = [];
  const db = {prepare: () => ({bind: v => ({first: async () => { rows.push(v); return {n: 0}; }}), first: async () => ({n: 0}), all: async () => ({results: [], meta: {}})})};
  const fail = () => { throw new Error('over'); };
  const t = Date.UTC(2026, 9, 14, 15, 0, 0) / 1000;   // 2026-10-15 00:00 JST
  await checkNewAccount(db, {}, fail, t);
  await checkNewAccount(db, {}, fail, t - 1);
  assert.deepEqual(rows, [t, t - 86400]);
});
