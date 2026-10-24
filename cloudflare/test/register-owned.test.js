// 「観た公演を追加」から、これからの公演を購入済に入れる（起案者の指示 2026-10-24「『観た公演を追加』、過去の記録じゃなくて
// 購入済の公演もここから探して追加できるようにして」）。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {setup, step, signIn} from './screens/harness.js';

const here = p => new URL(p, import.meta.url).pathname;
const FIXTURE = JSON.parse(execFileSync('python3', [here('./screens/recommend_fixture.py')], {encoding: 'utf8', maxBuffer: 64 * 1024 * 1024}));
function world() {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  // 今日は 2026-10-12。101 はこれから（11/1〜11/10）、102 は会期中（10/1〜10/20）
  for (const t of ['rec_card', 'rec_stage']) {
    sqlite.exec(`UPDATE ${t} SET start='2026-11-01', end='2026-11-10' WHERE stage_id='101'`);
    sqlite.exec(`UPDATE ${t} SET start='2026-10-01', end='2026-10-20' WHERE stage_id='102'`);
  }
  sqlite.exec("UPDATE rec_stage SET entry=json_set(entry,'$.period','2026/11/01 ～ 2026/11/10') WHERE stage_id='101'");
  sqlite.exec("DELETE FROM catalogue WHERE id IN ('101','102')");
  return {env, sqlite};
}
const add = (env, a, body) => step(env, a, {post: '/api/add_work', body});
const count = (sqlite, sql) => sqlite.prepare(sql).get().n;

test('a coming show with a future date goes to 購入済 with that day as the day to go, not to the records', async () => {
  const {env, sqlite} = world();
  const a = await signIn(env);
  try {
    const r = await add(env, a, {title: '舞台ひとつめ', date: '2026-11-03', time: '13:00', stage_id: '101'});
    assert.equal(r.status, 200);
    assert.equal(r.body.owned, true);
    assert.equal(count(sqlite, "SELECT count(*) AS n FROM works"), 0);
    assert.equal(count(sqlite, "SELECT count(*) AS n FROM reaction WHERE stage_id='101' AND owned=1"), 1);
    assert.equal(count(sqlite, "SELECT count(*) AS n FROM ticket WHERE stage_id='101' AND date='2026-11-03' AND time='13:00'"), 1);
    assert.match((await step(env, a, {get: '/api/screen/tickets'})).body.body_html, /data-stage="101"/);
  } finally { sqlite.close(); }
});

test('a coming show without a date also goes to 購入済; a date outside the run is refused without writing', async () => {
  const {env, sqlite} = world();
  const a = await signIn(env);
  try {
    const bad = await add(env, a, {title: '舞台ひとつめ', date: '2026-12-24', stage_id: '101'});
    assert.equal(bad.status, 400);
    assert.equal(count(sqlite, "SELECT count(*) AS n FROM reaction"), 0);
    const r = await add(env, a, {title: '舞台ひとつめ', date: '', stage_id: '101'});
    assert.equal(r.body.owned, true);
    assert.equal(count(sqlite, "SELECT count(*) AS n FROM ticket"), 0);
  } finally { sqlite.close(); }
});

test('a show seen already (past date, or running with no date) is still saved as a record', async () => {
  const {env, sqlite} = world();
  const a = await signIn(env);
  try {
    const r = await add(env, a, {title: '舞台ふたつめ', date: '2026-10-05', stage_id: '102'});
    assert.ok(r.body.work_key);
    assert.equal(r.body.owned, undefined);
    const r2 = await add(env, a, {title: '舞台ふたつめ', date: '', stage_id: '102'});
    assert.ok(r2.body.work_key);
    assert.equal(count(sqlite, "SELECT count(*) AS n FROM reaction"), 0);
  } finally { sqlite.close(); }
});
