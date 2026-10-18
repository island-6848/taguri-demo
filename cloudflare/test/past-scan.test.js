// 過去の公演を一覧から探す回数（screens/lists.js の takePastScan）: 全体の 1 日の上限に加えて、1 人ずつの上限（issue #73）。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync, readdirSync} from 'node:fs';
import {takePastScan, PAST_SCANS_PER_USER_DAY} from '../src/screens/lists.js';

function db() {
  const sqlite = new DatabaseSync(':memory:');
  for (const f of readdirSync(new URL('../migrations/', import.meta.url)).filter(n => n.endsWith('.sql')).sort()) sqlite.exec(readFileSync(new URL(`../migrations/${f}`, import.meta.url), 'utf8'));
  const wrap = (sql, args = []) => ({bind(...v) { return wrap(sql, v); }, async first() { return sqlite.prepare(sql).get(...args) ?? null; }, async all() { return {results: sqlite.prepare(sql).all(...args)}; }, async run() { return sqlite.prepare(sql).run(...args); }});
  return {sqlite, d1: {prepare: sql => wrap(sql), async batch(cs) { for (const c of cs) await c.run(); }}};
}

test('one user cannot use up the day\'s past-stage scans; the next day starts again', async () => {
  const {sqlite, d1} = db();
  const a = {db: d1, uid: 'a', today: '2026-10-18'}, b = {db: d1, uid: 'b', today: '2026-10-18'};
  for (let i = 0; i < PAST_SCANS_PER_USER_DAY; i++) assert.equal(await takePastScan(a), true);
  assert.equal(await takePastScan(a), false);
  assert.equal(await takePastScan(b), true);
  assert.equal(sqlite.prepare("SELECT v FROM rec_meta WHERE k='past_scan'").get().v, `2026-10-18 ${PAST_SCANS_PER_USER_DAY + 1}`);
  // 利用者の ID は書かない。前の日の数は次の日に消える
  for (const {k} of sqlite.prepare("SELECT k FROM usage WHERE k LIKE 'pastscan:%'").all()) assert.doesNotMatch(k, /:a$|:b$/);
  assert.equal(await takePastScan({...a, today: '2026-10-19'}), true);
  assert.equal(sqlite.prepare("SELECT count(*) AS n FROM usage WHERE k LIKE 'pastscan:2026-10-18:%'").get().n, 0);
});

test('the overall cap still stops everyone', async () => {
  const {sqlite, d1} = db();
  sqlite.prepare("INSERT INTO rec_meta(k,v) VALUES('past_scan','2026-10-18 150')").run();
  assert.equal(await takePastScan({db: d1, uid: 'c', today: '2026-10-18'}), false);
});
