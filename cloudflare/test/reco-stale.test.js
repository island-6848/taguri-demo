// 古いおすすめの控えは計算し直さずに出し、答えた公演だけ外す。計算し直しは夜の段（ctx.recompute）だけ
// （起案者の決定 2026-10-24「A で進めて」、dec-reco-nightly・f-reco-recompute-cpu-1021）
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {setup, step, signIn} from './screens/harness.js';
import {rankedGroups} from '../src/screens/recommend.js';

const here = p => new URL(p, import.meta.url).pathname;
const FIXTURE = JSON.parse(execFileSync('python3', [here('./screens/recommend_fixture.py')], {encoding: 'utf8', maxBuffer: 64 * 1024 * 1024}));

test('a stale cache is served as it is, without the stages answered since; only the nightly run recomputes', async () => {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  const u = await signIn(env);
  try {
    const key = (await step(env, u, {post: '/api/add_work', body: {title: '終わった舞台', date: '2026-08-05'}})).body.work_key;
    await step(env, u, {post: '/api/link_stage', body: {work_key: key, stage_id: '103'}});
    await step(env, u, {post: '/api/rate', body: {work_key: key, verdict: '◎'}});
    const other = (await step(env, u, {post: '/api/add_work', body: {title: '一日だけの舞台', date: '2026-09-05'}})).body.work_key;
    await step(env, u, {post: '/api/link_stage', body: {work_key: other, stage_id: '104'}});
    await step(env, u, {post: '/api/rate', body: {work_key: other, verdict: '×'}});
    const uid = sqlite.prepare('SELECT user_id FROM works WHERE work_key=?').get(key).user_id;
    const prod = {...env, RECO_INLINE: undefined};                // 本番と同じ（その場で計算し直さない）
    const ctx = {db: env.DB, env: prod, uid, today: env.CLOCK.today, now: env.CLOCK.now};
    const first = await rankedGroups(ctx);
    assert.equal(first.cached, false, 'no cache yet: computed once');
    assert.ok(first.groups.length >= 1);
    // 評価を付け直しても、計算し直さずに前の並びを出す
    await step(env, u, {post: '/api/rate', body: {work_key: key, verdict: '×'}});
    const stale = await rankedGroups(ctx);
    assert.equal(stale.cached, true);
    assert.equal(stale.stale, true);
    assert.deepEqual(stale.groups.map(g => g.stage_id), first.groups.map(g => g.stage_id));
    // そのあと答えた公演は外す
    const top = first.groups[0].stage_id;
    assert.equal((await step(env, u, {post: '/api/react', body: {stage_id: top, value: 'nointerest', nofill: true}})).status, 200);
    const after = await rankedGroups(ctx);
    assert.ok(!after.groups.some(g => g.stage_id === top), 'the answered stage is left out');
    assert.equal(after.groups.length, first.groups.length - 1);
    // 夜の段の計算（recompute）は計算し直し、そのあとは新しい控えに当たる
    const night = await rankedGroups({...ctx, recompute: true});
    assert.equal(night.cached, false);
    assert.notDeepEqual(night.groups.map(g => g.stage_id), first.groups.map(g => g.stage_id));
    const next = await rankedGroups(ctx);
    assert.equal(next.cached, true);
    assert.equal(next.stale, undefined);
  } finally { sqlite.close(); }
});
