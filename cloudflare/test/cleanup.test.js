// 記録の無いアカウントを 1 か月で片付ける（src/cleanup.js、起案者の指示 2026-10-18「1ヶ月で消してほしい」）。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync, readdirSync} from 'node:fs';
import {sweepEmptyAccounts, EMPTY_ACCOUNT_DAYS, ACCOUNT_TABLES} from '../src/cleanup.js';
import worker from '../src/worker.js';

function db() {
  const sqlite = new DatabaseSync(':memory:');
  for (const f of readdirSync(new URL('../migrations/', import.meta.url)).filter(n => n.endsWith('.sql')).sort()) sqlite.exec(readFileSync(new URL(`../migrations/${f}`, import.meta.url), 'utf8'));
  const wrap = (sql, args = []) => ({bind(...v) { return wrap(sql, v); }, async first() { return sqlite.prepare(sql).get(...args) ?? null; }, async all() { return {results: sqlite.prepare(sql).all(...args)}; }, async run() { return sqlite.prepare(sql).run(...args); }});
  return {sqlite, d1: {prepare: sql => wrap(sql), async batch(cs) { sqlite.exec('BEGIN'); try { for (const c of cs) await c.run(); sqlite.exec('COMMIT'); } catch (e) { sqlite.exec('ROLLBACK'); throw e; } }}};
}
const NOW = 1_800_000_000, DAY = 86400;
const user = (sqlite, id, ageDays) => sqlite.prepare('INSERT INTO users(id,recovery_hash,created_at) VALUES(?,?,?)').run(id, 'h-' + id, NOW - ageDays * DAY);

test('an account with no records, older than a month and not signed in for a month, is removed; others stay', async () => {
  const {sqlite, d1} = db();
  user(sqlite, 'old-empty', EMPTY_ACCOUNT_DAYS + 1);
  user(sqlite, 'new-empty', EMPTY_ACCOUNT_DAYS - 1);
  user(sqlite, 'old-with-work', 90);
  user(sqlite, 'old-with-fav', 90);
  user(sqlite, 'old-signed-in', 90);
  sqlite.prepare("INSERT INTO works(user_id,work_key,title,updated_at) VALUES('old-with-work','k','題','2026-01-01 00:00:00')").run();
  sqlite.prepare("INSERT INTO favourites(user_id,name,kind) VALUES('old-with-fav','名前','人')").run();
  sqlite.prepare('INSERT INTO sessions(hash,user_id,expires_at,created_at) VALUES(?,?,?,?)').run('s1', 'old-signed-in', NOW + DAY, NOW - 2 * DAY);
  // 設定・控えだけ、古いセッションだけのアカウントは、記録が無いので消える
  sqlite.prepare("INSERT INTO app_setting(user_id,key,value,updated_at) VALUES('old-empty','scale','star','x')").run();
  sqlite.prepare('INSERT INTO sessions(hash,user_id,expires_at,created_at) VALUES(?,?,?,?)').run('s0', 'old-empty', NOW - 40 * DAY, NOW - 70 * DAY);
  assert.equal(await sweepEmptyAccounts(d1, NOW), 1);
  const left = sqlite.prepare('SELECT id FROM users ORDER BY id').all().map(r => r.id);
  assert.deepEqual(left, ['new-empty', 'old-signed-in', 'old-with-fav', 'old-with-work']);
  for (const t of ACCOUNT_TABLES) assert.equal(sqlite.prepare(`SELECT count(*) AS n FROM ${t} WHERE user_id='old-empty'`).get().n, 0, t);
  assert.equal(await sweepEmptyAccounts(d1, NOW), 0);          // 2 回目は何もしない
});

test('the Worker has the daily scheduled handler and the cron', () => {
  assert.equal(typeof worker.scheduled, 'function');
  assert.match(readFileSync(new URL('../wrangler.jsonc', import.meta.url), 'utf8'), /"triggers":\s*\{\s*"crons":\s*\["[^"]+"\]/);
});
