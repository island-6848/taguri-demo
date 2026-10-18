// Request limits (src/rate-limit.js): a brake per visitor from the Rate
// Limiting binding, and an exact daily cap on new accounts.
import {DatabaseSync} from 'node:sqlite';
import {readFileSync, readdirSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import worker from '../src/worker.js';
import {limitKind, checkNewAccount, rateLimitHealth, resetRateLimitStatus, rlStatus, FAILING_MS} from '../src/rate-limit.js';
import {TERMS_VERSION} from '../src/terms.js';

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
  const post = (path, ip) => worker.fetch(new Request(ORIGIN + path, {method: 'POST', headers: {origin: ORIGIN, 'content-type': 'application/json', 'cf-connecting-ip': ip}, body: JSON.stringify({agree: TERMS_VERSION})}), env);
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

// 安全の点検 2026-10-17: 1 つの接続元から 1 日の新規登録の枠（と総数の上限）を使い切れない
test('one address makes at most 3 accounts a day; another address still can, and the next day it resets', async () => {
  const {post, sqlite} = setup();
  const codes = [];
  for (let i = 0; i < 4; i++) codes.push((await post('/api/register', '198.51.100.7')).status);
  assert.deepEqual(codes, [200, 200, 200, 429]);
  assert.match((await (await post('/api/register', '198.51.100.7')).json()).error, /同じ場所/);
  assert.equal((await post('/api/register', '203.0.113.8')).status, 200);
  assert.equal(sqlite.prepare('SELECT count(*) AS n FROM users').get().n, 4);
  // the address itself is not kept, only a hash with the day
  assert.ok(sqlite.prepare("SELECT k FROM usage WHERE k LIKE 'newacct:%'").all().every(r => !r.k.includes('198.51')));
  sqlite.prepare("UPDATE usage SET k=replace(k, substr(k, 9, 10), '2000-01-01') WHERE k LIKE 'newacct:%'").run();
  assert.equal((await post('/api/register', '198.51.100.7')).status, 200);
  assert.equal(sqlite.prepare("SELECT count(*) AS n FROM usage WHERE k LIKE 'newacct:2000%'").get().n, 0);
});

// issue #124: 同時に来た登録が、同じ残り枠を読んでそろって通らない。どの要求も下見を読み終えてから
// 書き込みに進むように止めておき（いちばん食い違いやすい順）、D1 のように batch を 1 つずつ実行する
function racing(n, extra = {}) {
  const s = setup(extra);
  const batch = s.env.DB.batch;
  let waiting = 0, release; const all = new Promise(r => { release = r; });
  let chain = Promise.resolve();
  s.env.DB.batch = async cs => {
    if (++waiting >= n) release();
    await all;
    const run = chain.then(() => batch(cs)); chain = run.catch(() => {}); return run;
  };
  return s;
}
const users = sqlite => sqlite.prepare('SELECT count(*) AS n FROM users').get().n;

test('ten sign-ups at once from one address make only 3 accounts, and the counter matches', async () => {
  const {post, sqlite} = racing(10);
  const codes = (await Promise.all(Array.from({length: 10}, () => post('/api/register', '198.51.100.9')))).map(r => r.status);
  assert.equal(codes.filter(c => c === 200).length, 3, String(codes));
  assert.ok(codes.filter(c => c !== 200).every(c => c === 429), String(codes));
  assert.equal(users(sqlite), 3);
  assert.equal(sqlite.prepare("SELECT n FROM usage WHERE k LIKE 'newacct:%'").get().n, 3);
  // 断られた要求はセッションを残さない
  assert.equal(sqlite.prepare('SELECT count(*) AS n FROM sessions').get().n, 3);
});

test('sign-ups at once from many addresses stop at the daily cap and at the total cap', async () => {
  const day = racing(6, {NEW_ACCOUNTS_PER_DAY: '2'});
  const a = (await Promise.all(Array.from({length: 6}, (_, i) => day.post('/api/register', `192.0.2.${i}`)))).map(r => r.status);
  assert.equal(a.filter(c => c === 200).length, 2, String(a));
  assert.equal(users(day.sqlite), 2);
  // 断られた接続元の数は増えない
  assert.equal(day.sqlite.prepare("SELECT count(*) AS n FROM usage WHERE k LIKE 'newacct:%'").get().n, 2);
  const total = racing(6, {MAX_ACCOUNTS: '4'});
  total.sqlite.exec("INSERT INTO users(id,recovery_hash,created_at) VALUES('old1','h1',0),('old2','h2',0)");
  const b = (await Promise.all(Array.from({length: 6}, (_, i) => total.post('/api/register', `192.0.2.${i}`)))).map(r => r.status);
  assert.equal(b.filter(c => c === 200).length, 2, String(b));
  assert.ok(b.filter(c => c !== 200).every(c => c === 503), String(b));
  assert.equal(users(total.sqlite), 4);
});

test('the sign-up check only reads: nothing is counted until the account is written', async () => {
  const {env, sqlite} = setup();
  const request = new Request(ORIGIN + '/api/register', {headers: {'cf-connecting-ip': '198.51.100.3'}});
  const fail = (status, message) => { throw Object.assign(new Error(message), {status}); };
  for (let i = 0; i < 5; i++) await checkNewAccount(env.DB, env, fail, undefined, request);
  assert.equal(sqlite.prepare('SELECT count(*) AS n FROM usage').get().n, 0);
});

// issue #133: missing binding, a failing binding and a normal 429 are told apart in /api/health,
// and the log says which kind failed without the address or the key.
test('health tells a missing binding, a failing one and normal limiting apart, and logs no address', async () => {
  const logs = [];
  const real = console.log; console.log = (...a) => logs.push(a.join(' '));
  try {
    resetRateLimitStatus();
    const missing = setup();
    assert.equal((await missing.post('/api/register', '198.51.100.21')).status, 200);
    let h = await (await missing.get('/api/health', '198.51.100.21')).json();
    assert.deepEqual([h.rate_limit.any.state, h.rate_limit.auth.state], ['missing', 'missing']);

    resetRateLimitStatus();
    const broken = {async limit() { throw new TypeError('down 198.51.100.22'); }};
    const failing = setup({RL_ANY: limiter(1000), RL_AUTH: broken});
    assert.equal((await failing.post('/api/register', '198.51.100.22')).status, 200);   // still passes
    assert.equal((await failing.post('/api/register', '198.51.100.22')).status, 200);
    h = await (await failing.get('/api/health', '198.51.100.22')).json();
    assert.equal(h.rate_limit.any.state, 'ok');
    assert.equal(h.rate_limit.auth.state, 'failing');
    assert.equal(h.rate_limit.auth.errors, 2);

    resetRateLimitStatus();
    const working = setup({RL_ANY: limiter(1000), RL_AUTH: limiter(1)});
    assert.equal((await working.post('/api/register', '198.51.100.23')).status, 200);
    assert.equal((await working.post('/api/register', '198.51.100.23')).status, 429);
    h = await (await working.get('/api/health', '198.51.100.23')).json();
    assert.equal(h.rate_limit.auth.state, 'ok');
    assert.equal(h.rate_limit.auth.limited, 1);
    assert.equal(h.rate_limit.auth.errors, 0);

    const said = logs.filter(l => l.startsWith('rate limit'));
    assert.ok(said.some(l => /auth: binding failed \(TypeError\)/.test(l)), said.join('\n'));
    assert.ok(said.some(l => /any: no binding/.test(l)), said.join('\n'));
    assert.equal(said.filter(l => /binding failed/.test(l)).length, 1);           // once a minute, not per request
    for (const l of said) assert.doesNotMatch(l, /198\.51\.100|down/);
    assert.doesNotMatch(JSON.stringify(h.rate_limit), /198\.51\.100/);
  } finally { console.log = real; resetRateLimitStatus(); }
});

test('a failure shows as failing for ten minutes, then ok again', () => {
  resetRateLimitStatus();
  const env = {RL_ANY: {limit() {}}, RL_AUTH: {limit() {}}};
  rlStatus.auth.lastErrorAt = 1_000_000;
  assert.equal(rateLimitHealth(env, 1_000_000 + FAILING_MS - 1).auth.state, 'failing');
  assert.equal(rateLimitHealth(env, 1_000_000 + FAILING_MS).auth.state, 'ok');
  assert.equal(rateLimitHealth({}, 0).any.state, 'missing');
  resetRateLimitStatus();
});
