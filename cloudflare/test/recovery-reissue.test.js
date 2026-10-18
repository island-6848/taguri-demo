// 復旧コードの作り直し（issue #126）: 直近のログインが要り、古いコードは使えなくなり、新しいコードで入れる。
// ほかの端末はログアウトし、この端末はそのまま。
import {DatabaseSync} from 'node:sqlite';
import {readFileSync, readdirSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import worker from '../src/worker.js';
import {TERMS_VERSION} from '../src/terms.js';

const ORIGIN = 'https://taguri.example';
function setup() {
  const sqlite = new DatabaseSync(':memory:');
  for (const f of readdirSync(new URL('../migrations/', import.meta.url)).filter(n => n.endsWith('.sql')).sort()) sqlite.exec(readFileSync(new URL(`../migrations/${f}`, import.meta.url), 'utf8'));
  const wrap = (sql, args = []) => ({bind(...v) { return wrap(sql, v); }, async first() { return sqlite.prepare(sql).get(...args) ?? null; }, async all() { return {results: sqlite.prepare(sql).all(...args)}; }, async run() { return sqlite.prepare(sql).run(...args); }, async execute() { return /^SELECT/.test(sql) ? this.all() : this.run(); }});
  const env = {ALLOW_REGISTRATION: 'true', DB: {prepare: sql => wrap(sql), async batch(cs) { sqlite.exec('BEGIN'); try { const r = []; for (const c of cs) r.push(await c.execute()); sqlite.exec('COMMIT'); return r; } catch (e) { sqlite.exec('ROLLBACK'); throw e; } }}, ASSETS: {fetch: () => new Response('static')}};
  const call = (path, value, cookie = '') => worker.fetch(new Request(`${ORIGIN}/api/${path}`, {method: value === undefined ? 'GET' : 'POST', headers: {cookie, origin: ORIGIN, 'content-type': 'application/json'}, body: value === undefined ? undefined : JSON.stringify(value)}), env);
  return {call, sqlite, env};
}
const cookieOf = r => r.headers.get('set-cookie')?.split(';')[0] ?? '';

test('a fresh sign-in can reissue the recovery code: the old one stops, the new one works, other devices sign out', async () => {
  const {call, sqlite} = setup();
  const reg = await call('register', {agree: TERMS_VERSION});
  const here = cookieOf(reg), {recovery_code: old} = await reg.json();
  await call('record', {id: 'r1', title: '残る記録', date: '2026-09-01'}, here);
  const other = cookieOf(await call('recover', {code: old}));
  const r = await call('recovery/reissue', {}, here);
  assert.equal(r.status, 200);
  const {recovery_code: fresh} = await r.json();
  assert.match(fresh, /^[a-f0-9]{64}$/);
  assert.notEqual(fresh, old);
  assert.equal((await call('recover', {code: old})).status, 401);
  const back = await call('recover', {code: fresh});
  assert.equal(back.status, 200);
  assert.equal((await (await call('state', undefined, cookieOf(back))).json()).records[0].title, '残る記録');
  // ほかの端末はログアウト、この端末は続けて使える
  assert.equal((await call('state', undefined, other)).status, 401);
  assert.equal((await call('state', undefined, here)).status, 200);
  assert.ok(!JSON.stringify(sqlite.prepare('SELECT * FROM users').all()).includes(fresh));
});

test('reissuing needs a sign-in within 10 minutes, and accounts without a recovery code get none', async () => {
  const {call, sqlite} = setup();
  const reg = await call('register', {agree: TERMS_VERSION});
  const cookie = cookieOf(reg), {recovery_code: old} = await reg.json();
  sqlite.exec('UPDATE sessions SET created_at = created_at - 3600');
  const r = await call('recovery/reissue', {}, cookie);
  assert.equal(r.status, 401);
  assert.match((await r.json()).error, /10分以内/);
  assert.equal((await call('recover', {code: old})).status, 200);   // 古いコードはそのまま
  assert.equal((await call('recovery/reissue', {})).status, 401);    // ログインしていない
  // Google・メールで始めたアカウントは復旧コードを持たないので作らない
  const fresh = cookieOf(await call('recover', {code: old}));
  sqlite.exec("UPDATE users SET recovery_hash='firebase:x'");
  assert.equal((await call('recovery/reissue', {}, fresh)).status, 409);
  assert.equal(sqlite.prepare('SELECT recovery_hash FROM users').get().recovery_hash, 'firebase:x');
});

test('a sign-in with the old code that races the reissue gets no session', async () => {
  const {call, sqlite, env} = setup();
  const reg = await call('register', {agree: TERMS_VERSION});
  const cookie = cookieOf(reg), {recovery_code: old} = await reg.json();
  // 古いコードで利用者を読んだあと、セッションを書く前に作り直しが入る順
  const batch = env.DB.batch;
  let once = true;
  env.DB.batch = async cs => { if (once) { once = false; env.DB.batch = batch; await call('recovery/reissue', {}, cookie); } return batch(cs); };
  const late = await call('recover', {code: old});
  assert.equal(late.status, 401);
  assert.equal(sqlite.prepare('SELECT count(*) AS n FROM sessions').get().n, 1);   // 作り直した端末だけ
});
