// 同じ秒に評価を付け直しても、おすすめの控え（rec_cache）を使い回さない（issue #189、migrations/0035 の rec_rev）
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {setup, step, signIn} from './screens/harness.js';
import {rankedGroups} from '../src/screens/recommend.js';

const here = p => new URL(p, import.meta.url).pathname;
const FIXTURE = JSON.parse(execFileSync('python3', [here('./screens/recommend_fixture.py')], {encoding: 'utf8', maxBuffer: 64 * 1024 * 1024}));

test('re-rating in the same second is not answered from the cache, and the hidden check is chosen again', async () => {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  const u = await signIn(env);
  try {
    const key = (await step(env, u, {post: '/api/add_work', body: {title: '終わった舞台', date: '2026-08-05'}})).body.work_key;
    assert.equal((await step(env, u, {post: '/api/link_stage', body: {work_key: key, stage_id: '103'}})).status, 200);
    assert.equal((await step(env, u, {post: '/api/rate', body: {work_key: key, verdict: '◎'}})).status, 200);
    const other = (await step(env, u, {post: '/api/add_work', body: {title: '一日だけの舞台', date: '2026-09-05'}})).body.work_key;
    assert.equal((await step(env, u, {post: '/api/link_stage', body: {work_key: other, stage_id: '104'}})).status, 200);
    assert.equal((await step(env, u, {post: '/api/rate', body: {work_key: other, verdict: '×'}})).status, 200);
    const uid = sqlite.prepare('SELECT user_id FROM works WHERE work_key=?').get(key).user_id;
    const ctx = {db: env.DB, env, uid, today: env.CLOCK.today, now: env.CLOCK.now};
    const first = await rankedGroups(ctx);
    assert.equal(first.cached, false);
    assert.ok(first.groups.length, 'the ◎ brings recommendations');
    assert.equal((await rankedGroups(ctx)).cached, true);
    // 時計は止まったまま（同じ秒）で ◎ を × に
    assert.equal((await step(env, u, {post: '/api/rate', body: {work_key: key, verdict: '×'}})).status, 200);
    const again = await rankedGroups(ctx);
    assert.equal(again.cached, false);
    assert.notDeepEqual(again.groups.map(g => g.stage_id), first.groups.map(g => g.stage_id));
    const {rec_rev: rr, works_rev: wr} = sqlite.prepare('SELECT rec_rev, works_rev FROM users WHERE id=?').get(uid);
    assert.ok(rr >= wr && wr >= 7, `rec_rev ${rr}, works_rev ${wr}`);    // 2 件の追加・つなぎ・評価と、付け直し
  } finally { sqlite.close(); }
});
