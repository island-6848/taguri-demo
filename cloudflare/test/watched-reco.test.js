// 観劇記録に足した公演（起案者の指摘 2026-10-20「観劇記録に追加しても、すぐにおすすめ欄に反映されてる感じしない」、
// dec-watched-unrated-seed）: 記録にある公演はおすすめから外し、評価する前から購入済みと同じ種にする。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {setup, step, signIn} from './screens/harness.js';

const here = p => new URL(p, import.meta.url).pathname;
const FIXTURE = JSON.parse(execFileSync('python3', [here('./screens/recommend_fixture.py')], {encoding: 'utf8', maxBuffer: 64 * 1024 * 1024}));
const stages = html => [...new Set([...html.matchAll(/data-stage="(\d+)"/g)].map(m => m[1]))];

test('a stage in the records leaves the recommendations, and an unrated record already seeds them', async () => {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  // 101（俳優乙・俳優甲）は上演中、102（俳優乙）はこれから
  sqlite.exec("UPDATE rec_stage SET start='2026-10-01', end='2026-11-10' WHERE stage_id='101'");
  sqlite.exec("UPDATE rec_stage SET start='2026-12-01', end='2026-12-10' WHERE stage_id='102'");
  const a = await signIn(env);
  const rec = async () => stages((await step(env, a, {get: '/api/screen/recommend'})).body.body_html);
  try {
    // 101 を ◎ で興味ありにしていた人の続き（評価のある記録が 1 件ある）
    const k0 = (await step(env, a, {post: '/api/add_work', body: {title: '一日だけ', date: '2026-09-05'}})).body.work_key;
    await step(env, a, {post: '/api/link_stage', body: {work_key: k0, stage_id: '104'}});
    await step(env, a, {post: '/api/rate', body: {work_key: k0, verdict: '×'}});
    assert.ok(!(await rec()).includes('102'), '記録の前は 102 が出ない');
    // 101 を観て、記録に足しただけ（評価はまだ）
    const add = await step(env, a, {post: '/api/add_work', body: {title: '舞台ひとつめ', date: '2026-10-11', stage_id: '101'}});
    assert.equal(add.status, 200);
    const after = await rec();
    assert.ok(!after.includes('101'), '観た 101 はおすすめから外れる');
    assert.ok(after.includes('102'), '評価の前から、101 の俳優乙で 102 が上がる');
    // 評価を付けると、種ではなく評価 1 回分に替わる（× なら 102 は上がらない）
    await step(env, a, {post: '/api/rate', body: {work_key: add.body.work_key, verdict: '×'}});
    const rated = await rec();
    assert.ok(!rated.includes('101') && !rated.includes('102'), JSON.stringify(rated));
  } finally { sqlite.close(); }
});
