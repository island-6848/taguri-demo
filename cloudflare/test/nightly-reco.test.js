// 夜の段の「おすすめを全員分前もって作る」（scripts/nightly_reco.mjs、dec-reco-nightly）。本番の D1 の代わりに
// 試験の SQLite に同じ問い合わせを送り、作った控えを Worker がそのまま使えること、その場で計算したのと同じ並びになることを確かめる
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {setup, step, signIn} from './screens/harness.js';
import {rankedGroups} from '../src/screens/recommend.js';
import {run, TABLES} from '../scripts/nightly_reco.mjs';

const here = p => new URL(p, import.meta.url).pathname;
const FIXTURE = JSON.parse(execFileSync('python3', [here('./screens/recommend_fixture.py')], {encoding: 'utf8', maxBuffer: 64 * 1024 * 1024}));

test('the nightly run writes caches the Worker uses as they are, ranked as a fresh computation', async () => {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  const remote = async (sql, params = []) => { const results = sqlite.prepare(sql).all(...params); return {results, rows_read: results.length}; };
  const prod = {...env, RECO_INLINE: undefined};
  try {
    const uids = [];
    for (const [title, sid, v, date] of [['終わった舞台', '103', '◎', '2026-08-05'], ['一日だけの舞台', '104', '×', '2026-09-05']]) {
      const u = await signIn(env);
      const key = (await step(env, u, {post: '/api/add_work', body: {title, date}})).body.work_key;
      await step(env, u, {post: '/api/link_stage', body: {work_key: key, stage_id: sid}});
      await step(env, u, {post: '/api/rate', body: {work_key: key, verdict: v}});
      const uid = sqlite.prepare('SELECT user_id FROM works WHERE work_key=?').get(key).user_id;
      uids.push(uid);
      // 一度画面で計算して控えを作り、そのあと評価を付け直して控えを古くする
      await rankedGroups({db: env.DB, env: prod, uid, today: env.CLOCK.today, now: env.CLOCK.now});
      await step(env, u, {post: '/api/rate', body: {work_key: key, verdict: v === '◎' ? '×' : '◎'}});
      assert.equal((await rankedGroups({db: env.DB, env: prod, uid, today: env.CLOCK.today, now: env.CLOCK.now})).stale, true);
    }
    const out = await run(remote, {today: env.CLOCK.today, now: env.CLOCK.now + 5000});
    assert.equal(out.failed, 0);
    assert.equal(out.computed, uids.length);
    assert.equal(out.written, uids.length);
    assert.ok(out.rows_read > 0);
    for (const uid of uids) {
      const ctx = {db: env.DB, env: prod, uid, today: env.CLOCK.today, now: env.CLOCK.now};
      const served = await rankedGroups(ctx);
      assert.equal(served.cached, true);
      assert.equal(served.stale, undefined, 'the nightly cache carries the current stamp');
      const fresh = await rankedGroups({...ctx, recompute: true});
      assert.deepEqual(served.groups.map(g => g.stage_id), fresh.groups.map(g => g.stage_id));
    }
    // 2 回目は何も変わらないので書かない
    const again = await run(remote, {today: env.CLOCK.today, now: env.CLOCK.now + 10000});
    assert.equal(again.written, 0);
    // 写す表は、どれも migration にある
    const have = new Set(sqlite.prepare("SELECT name FROM sqlite_master WHERE type='table'").all().map(r => r.name));
    for (const t of TABLES) assert.ok(have.has(t), t);
  } finally { sqlite.close(); }
});

test('a cache the Worker rebuilt after the nightly run started is not overwritten', async () => {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  const remote = async (sql, params = []) => { const results = sqlite.prepare(sql).all(...params); return {results, rows_read: results.length}; };
  try {
    const u = await signIn(env);
    const key = (await step(env, u, {post: '/api/add_work', body: {title: '終わった舞台', date: '2026-08-05'}})).body.work_key;
    await step(env, u, {post: '/api/link_stage', body: {work_key: key, stage_id: '103'}});
    await step(env, u, {post: '/api/rate', body: {work_key: key, verdict: '◎'}});
    const uid = sqlite.prepare('SELECT user_id FROM works WHERE work_key=?').get(key).user_id;
    await rankedGroups({db: env.DB, env: {}, uid, today: env.CLOCK.today, now: env.CLOCK.now});
    sqlite.prepare("UPDATE rec_cache SET stamp='', created_at=? WHERE user_id=?").run(Math.floor(env.CLOCK.now / 1000) + 100, uid);
    const out = await run(remote, {today: env.CLOCK.today, now: env.CLOCK.now});
    assert.equal(out.written, 0);
    assert.equal(out.skipped, 1);
    assert.equal(sqlite.prepare('SELECT stamp FROM rec_cache WHERE user_id=?').get(uid).stamp, '');
  } finally { sqlite.close(); }
});
