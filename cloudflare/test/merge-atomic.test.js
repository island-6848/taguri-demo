// 記録をまとめる（merge_work）書き込みは 1 つの batch（issue #187）。前はまとめた印を先に書き、評価・感想の移動と
// 手で入れた出演者の移動を別々に書いていたので、途中で失敗すると印だけが残り、評価の無い記録が 1 件隠れた。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {setup, step, signIn} from './screens/harness.js';

const uidOf = (sqlite, key) => sqlite.prepare('SELECT user_id FROM works WHERE work_key=?').get(key).user_id;
const rowsOf = (sqlite, uid) => ({
  hand: sqlite.prepare('SELECT work_key, fields FROM hand_credits WHERE user_id=? ORDER BY work_key').all(uid).map(r => [r.work_key, r.fields]),
  merges: sqlite.prepare('SELECT work_key, into_key FROM merges WHERE user_id=? ORDER BY work_key').all(uid).map(r => [r.work_key, r.into_key]),
  works: sqlite.prepare('SELECT work_key, verdict, note_impression, rated_at FROM works WHERE user_id=? ORDER BY work_key').all(uid).map(r => ({...r})),
});

/** env.DB の、sql が pattern に合う文だけ失敗させる（batch の中でも、単独の run でも） */
function faulty(env, pattern) {
  const db = env.DB;
  const fail = () => { throw new Error('injected'); };
  const broken = {bind() { return broken; }, run: fail, execute: fail, first: fail, all: fail};
  return {...env, DB: {...db, prepare: sql => pattern.test(sql) ? broken : db.prepare(sql)}};
}

for (const [stage, pattern] of [['the rating move', /verdict=COALESCE/], ['the hand credits move', /^INSERT INTO hand_credits/]]) {
  test(`a merge that fails at ${stage} leaves nothing behind`, async () => {
    const {env, sqlite} = setup();
    const a = await signIn(env);
    try {
      const add = async (title, date) => (await step(env, a, {post: '/api/add_work', body: {title, date}})).body.work_key;
      const keep = await add('先に観た記録', '2026-08-01');
      const drop = await add('後で観た記録', '2026-08-02');
      assert.equal((await step(env, a, {post: '/api/rate', body: {work_key: drop, verdict: '◎'}})).status, 200);
      assert.equal((await step(env, a, {post: '/api/hand_credits', body: {work_key: drop, fields: {出演: '役者 二'}}})).status, 200);
      const uid = uidOf(sqlite, keep);
      const before = rowsOf(sqlite, uid);
      const r = await step(faulty(env, pattern), a, {post: '/api/merge_work', body: {work_key: keep, other: drop}});
      assert.notEqual(r.status, 200);
      assert.deepEqual(rowsOf(sqlite, uid), before);
      // 失敗しなければ、印・評価・出演者がそろって移る
      const ok = await step(env, a, {post: '/api/merge_work', body: {work_key: keep, other: drop}});
      assert.equal(ok.status, 200);
      assert.deepEqual(ok.body.moved, ['評価', '手で入れた出演者']);
      assert.equal(sqlite.prepare('SELECT verdict FROM works WHERE user_id=? AND work_key=?').get(uid, keep).verdict, '◎');
      assert.deepEqual(rowsOf(sqlite, uid).merges, [[drop, keep]]);
      assert.deepEqual(rowsOf(sqlite, uid).hand.map(([k]) => k), [drop, keep].sort());
    } finally { sqlite.close(); }
  });
}
