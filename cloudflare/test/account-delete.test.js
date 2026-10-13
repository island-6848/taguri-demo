// Account deletion (security rules R7): everything about the user goes, only
// after a fresh sign-in, and nobody else's data is touched.
import {DatabaseSync} from 'node:sqlite';
import {readFileSync, readdirSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import worker from '../src/worker.js';

const ORIGIN = 'https://taguri.example';
function setup() {
  const sqlite = new DatabaseSync(':memory:');
  for (const f of readdirSync(new URL('../migrations/', import.meta.url)).filter(n => n.endsWith('.sql')).sort()) sqlite.exec(readFileSync(new URL(`../migrations/${f}`, import.meta.url), 'utf8'));
  const wrap = (sql, args = []) => ({bind(...v) { return wrap(sql, v); }, async first() { return sqlite.prepare(sql).get(...args) ?? null; }, async all() { return {results: sqlite.prepare(sql).all(...args)}; }, async run() { return sqlite.prepare(sql).run(...args); }, async execute() { return /^SELECT/.test(sql) ? this.all() : this.run(); }});
  const env = {ALLOW_REGISTRATION: 'true', DB: {prepare: sql => wrap(sql), async batch(cs) { sqlite.exec('BEGIN'); try { const r = []; for (const c of cs) r.push(await c.execute()); sqlite.exec('COMMIT'); return r; } catch (e) { sqlite.exec('ROLLBACK'); throw e; } }}, ASSETS: {fetch: () => new Response('static')}};
  const call = (path, value, cookie = '', origin = ORIGIN) => worker.fetch(new Request(`${ORIGIN}/api/${path}`, {method: value === undefined ? 'GET' : 'POST', headers: {cookie, origin, 'content-type': 'application/json'}, body: value === undefined ? undefined : JSON.stringify(value)}), env);
  return {call, sqlite, env};
}
const cookieOf = r => r.headers.get('set-cookie')?.split(';')[0] ?? '';
async function account(call, sqlite, label) {
  const reg = await call('register', {});
  const cookie = cookieOf(reg), {recovery_code} = await reg.json();
  await call('record', {id: `${label}-r`, title: `${label}の記録`, date: '2026-09-01', rating: '◎', note: '感想'}, cookie);
  await call('favourite', {name: `${label}の作者`, kind: '人'}, cookie);
  await call('reaction', {stage_id: `${label}-s`, status: 'interest'}, cookie);
  const uid = sqlite.prepare('SELECT user_id FROM records WHERE id=?').get(`${label}-r`).user_id;
  sqlite.prepare("INSERT INTO passkeys(id,user_id,user_handle,public_key,created_at) VALUES(?,?,'h','k',0)").run(`${label}-key`, uid);
  sqlite.prepare("INSERT INTO webauthn_challenges(id,challenge,purpose,user_id,expires_at) VALUES(?,'c','register',?,?)").run(`${label}-ch`, uid, Math.floor(Date.now() / 1000) + 300);
  sqlite.prepare("INSERT INTO rec_cache(user_id,stamp,body,created_at) VALUES(?,'s','{}',0)").run(uid);
  return {cookie, recovery_code, uid};
}
const TABLES = ['users', 'sessions', 'records', 'favourites', 'reactions', 'passkeys', 'webauthn_challenges', 'rec_cache'];
const rowsOf = (sqlite, uid) => Object.fromEntries(TABLES.map(t => [t, sqlite.prepare(`SELECT count(*) AS n FROM ${t} WHERE ${t === 'users' ? 'id' : 'user_id'}=?`).get(uid).n]));

test('deleting removes every row of the account and nothing of anyone else', async () => {
  const {call, sqlite} = setup();
  const a = await account(call, sqlite, 'A'), b = await account(call, sqlite, 'B');
  const secondDevice = cookieOf(await call('recover', {code: a.recovery_code}));
  assert.ok(Object.values(rowsOf(sqlite, a.uid)).every(n => n > 0), JSON.stringify(rowsOf(sqlite, a.uid)));
  // Every table is cleared explicitly; this must not depend on FK cascades.
  sqlite.exec('PRAGMA foreign_keys = OFF');
  const res = await call('account/delete', {confirm: '削除'}, a.cookie);
  assert.equal(res.status, 200);
  assert.deepEqual(await res.json(), {deleted: true, firebase_linked: false});
  assert.match(res.headers.get('set-cookie'), /Max-Age=0/);
  assert.deepEqual(rowsOf(sqlite, a.uid), Object.fromEntries(TABLES.map(t => [t, 0])));
  // Nothing left anywhere that mentions the account's content.
  const dump = JSON.stringify(TABLES.map(t => sqlite.prepare(`SELECT * FROM ${t}`).all()));
  assert.ok(!dump.includes('Aの記録') && !dump.includes('Aの作者') && !dump.includes(a.uid));
  // No way back in: other devices and the recovery code are dead.
  assert.equal((await call('state', undefined, secondDevice)).status, 401);
  assert.equal((await call('recover', {code: a.recovery_code})).status, 401);
  // B is untouched.
  assert.ok(Object.values(rowsOf(sqlite, b.uid)).every(n => n > 0));
  assert.equal((await (await call('state', undefined, b.cookie)).json()).records[0].title, 'Bの記録');
});

test('a stale or legacy session cannot delete; a fresh sign-in can', async () => {
  const {call, sqlite} = setup();
  const a = await account(call, sqlite, 'A');
  sqlite.prepare('UPDATE sessions SET created_at=? WHERE user_id=?').run(Math.floor(Date.now() / 1000) - 601, a.uid);
  const stale = await call('account/delete', {confirm: '削除'}, a.cookie);
  assert.equal(stale.status, 401);
  assert.match((await stale.json()).error, /ログインし直して/);
  sqlite.prepare('UPDATE sessions SET created_at=NULL WHERE user_id=?').run(a.uid);              // sessions from before 0006
  assert.equal((await call('account/delete', {confirm: '削除'}, a.cookie)).status, 401);
  assert.equal(rowsOf(sqlite, a.uid).records, 1);
  // Signing in again (here with the recovery code) gives a fresh session that may delete.
  const fresh = cookieOf(await call('recover', {code: a.recovery_code}));
  assert.equal((await call('account/delete', {confirm: '削除'}, fresh)).status, 200);
  assert.equal(rowsOf(sqlite, a.uid).users, 0);
});

test('requires the typed confirmation, the same site and a signed-in user', async () => {
  const {call, sqlite} = setup();
  const a = await account(call, sqlite, 'A');
  for (const body of [{}, {confirm: 'delete'}, {confirm: ' 削除'}, {confirm: true}]) assert.equal((await call('account/delete', body, a.cookie)).status, 400, JSON.stringify(body));
  assert.equal((await call('account/delete', {confirm: '削除'}, a.cookie, 'https://evil.example')).status, 403);
  assert.equal((await call('account/delete', {confirm: '削除'}, '')).status, 401);
  assert.equal(rowsOf(sqlite, a.uid).records, 1);
});

test('a Google-linked account reports the link, and the same Google account later starts empty', async () => {
  const {call, sqlite} = setup();
  const a = await account(call, sqlite, 'A');
  sqlite.prepare("UPDATE users SET firebase_uid='google-1' WHERE id=?").run(a.uid);
  // Re-signed in some other way (no fresh Firebase user in the browser): refused, nothing deleted.
  const refused = await call('account/delete', {confirm: '削除'}, a.cookie);
  assert.equal(refused.status, 409);
  assert.equal(rowsOf(sqlite, a.uid).users, 1);
  const res = await call('account/delete', {confirm: '削除', firebase_ready: true}, a.cookie);
  assert.deepEqual(await res.json(), {deleted: true, firebase_linked: true});
  assert.equal(sqlite.prepare("SELECT count(*) AS n FROM users WHERE firebase_uid='google-1'").get().n, 0);
});

test('with the Render bridge on, deletion and recovery reach this Worker via /migration-api/', async () => {
  const {sqlite, env} = setup();
  env.ORIGINAL_UI_BRIDGE = 'true';
  const post = (path, value, cookie = '') => worker.fetch(new Request(`${ORIGIN}${path}`, {method: 'POST', headers: {cookie, origin: ORIGIN, 'content-type': 'application/json'}, body: JSON.stringify(value)}), env);
  const reg = await post('/migration-api/register', {});
  const {recovery_code} = await reg.json();
  const fresh = cookieOf(await post('/migration-api/recover', {code: recovery_code}));
  assert.match(fresh, /taguri_session=/);
  assert.equal((await post('/migration-api/account/delete', {confirm: '削除'}, fresh)).status, 200);
  assert.equal(sqlite.prepare('SELECT count(*) AS n FROM users').get().n, 0);
});
