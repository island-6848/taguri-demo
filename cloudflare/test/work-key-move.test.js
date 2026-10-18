// 記録の鍵（work_key = 題名#観た日）が変わるときの書き込み（issue #186）。題名・日付を直したら、手で入れた出演者
// （hand_credits）・まとめた印（merges）・取り消しの印（excluded の work:<key>）も同じ batch で新しい鍵へ移す。
// 前は works だけが動き、ほかの行が古い鍵のまま残って見えなくなった。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {setup, step, signIn} from './screens/harness.js';
import {loadWorks} from '../src/screens/works.js';

const ctxOf = (env, sqlite, key) => ({db: env.DB, uid: sqlite.prepare('SELECT user_id FROM works WHERE work_key=?').get(key).user_id,
  today: env.CLOCK.today, now: env.CLOCK.now});
const rowsOf = (sqlite, uid) => ({
  hand: sqlite.prepare('SELECT work_key FROM hand_credits WHERE user_id=? ORDER BY work_key').all(uid).map(r => r.work_key),
  merges: sqlite.prepare('SELECT work_key, into_key FROM merges WHERE user_id=? ORDER BY work_key').all(uid).map(r => [r.work_key, r.into_key]),
  excluded: sqlite.prepare('SELECT uid FROM excluded WHERE user_id=? ORDER BY uid').all(uid).map(r => r.uid),
});

test('renaming a record moves its hand credits and merges with it, and leaves the other user alone', async () => {
  const {env, sqlite} = setup();
  const a = await signIn(env), b = await signIn(env);
  try {
    const add = async (u, title, date) => (await step(env, u, {post: '/api/add_work', body: {title, date}})).body.work_key;
    const key = await add(a, '直す前の題', '2026-08-01');
    const dup = await add(a, '同じ舞台の別の記録', '2026-08-03');
    const bKey = await add(b, '直す前の題', '2026-08-01');
    assert.equal(bKey, key, 'the other user has the same key');
    for (const u of [a, b]) assert.equal((await step(env, u, {post: '/api/hand_credits', body: {work_key: key, fields: {出演: '役者 一'}}})).status, 200);
    assert.equal((await step(env, a, {post: '/api/merge_work', body: {work_key: key, other: dup}})).status, 200);
    const ctx = ctxOf(env, sqlite, dup), bCtx = {...ctx, uid: sqlite.prepare('SELECT id FROM users WHERE id<>?').get(ctx.uid).id};
    const bBefore = rowsOf(sqlite, bCtx.uid);

    const r = await step(env, a, {post: '/api/fix_work', body: {work_key: key, title: '直した後の題'}});
    assert.equal(r.status, 200);
    const moved = r.body.work_key;
    assert.notEqual(moved, key);
    const w = (await loadWorks({...ctx})).find(x => x.work_key === moved);
    assert.deepEqual(w.hand.fields, {出演: '役者 一'});
    assert.deepEqual(w.merged.map(m => m.work_key), [dup]);
    assert.deepEqual(rowsOf(sqlite, ctx.uid), {hand: [moved], merges: [[dup, moved]], excluded: []});
    assert.deepEqual(rowsOf(sqlite, bCtx.uid), bBefore);

    // まとめられた側（統合元）の鍵を直しても、印は付いたまま
    const r2 = await step(env, a, {post: '/api/fix_work', body: {work_key: dup, title: '別の記録の題'}});
    assert.equal(r2.status, 200);
    assert.deepEqual(rowsOf(sqlite, ctx.uid).merges, [[r2.body.work_key, moved]]);
    assert.deepEqual((await loadWorks({...ctx})).find(x => x.work_key === moved).merged.map(m => m.work_key), [r2.body.work_key]);
  } finally { sqlite.close(); }
});

test('renaming a dropped record keeps it dropped under the new key, and it can still be restored', async () => {
  const {env, sqlite} = setup();
  const a = await signIn(env);
  try {
    const key = (await step(env, a, {post: '/api/add_work', body: {title: '外した記録', date: '2026-08-01'}})).body.work_key;
    assert.equal((await step(env, a, {post: '/api/drop_work', body: {work_key: key}})).status, 200);
    const ctx = ctxOf(env, sqlite, key);
    const r = await step(env, a, {post: '/api/fix_work', body: {work_key: key, title: '外した記録の新しい題'}});
    assert.equal(r.status, 200);
    assert.deepEqual(rowsOf(sqlite, ctx.uid).excluded, [`work:${r.body.work_key}`]);
    assert.equal((await loadWorks({...ctx})).length, 0);
    assert.equal((await step(env, a, {post: '/api/restore_work', body: {key: r.body.work_key}})).status, 200);
    assert.deepEqual((await loadWorks({...ctx})).map(w => w.work_key), [r.body.work_key]);
  } finally { sqlite.close(); }
});

test('a row left behind under the new key by the old version does not block the rename', async () => {
  const {env, sqlite} = setup();
  const a = await signIn(env);
  try {
    const key = (await step(env, a, {post: '/api/add_work', body: {title: '今の題', date: '2026-08-01'}})).body.work_key;
    assert.equal((await step(env, a, {post: '/api/hand_credits', body: {work_key: key, fields: {出演: '今の役者'}}})).status, 200);
    const ctx = ctxOf(env, sqlite, key);
    sqlite.prepare(`INSERT INTO hand_credits(user_id,work_key,fields,updated_at) VALUES(?,'前の題#2026-08-01','{"出演":"古い役者"}','x')`).run(ctx.uid);
    const r = await step(env, a, {post: '/api/fix_work', body: {work_key: key, title: '前の題'}});
    assert.equal(r.status, 200);
    assert.deepEqual(rowsOf(sqlite, ctx.uid).hand, [r.body.work_key]);
    assert.deepEqual((await loadWorks({...ctx}))[0].hand.fields, {出演: '今の役者'});
  } finally { sqlite.close(); }
});
