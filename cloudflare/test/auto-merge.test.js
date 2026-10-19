// 同じ作品の記録を自動でまとめる（起案者の指示 2026-10-19「観劇記録の中でも回は違っても同じ作品なら同じ作品のツリーとして統合する作業を
// 自動でやって（今ユーザーの手動）」、diary.autoMerge）
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {setup, step, signIn} from './screens/harness.js';

async function withUser(fn) {
  const {env, sqlite} = setup();
  const a = await signIn(env);
  try { await fn(env, a, sqlite); } finally { sqlite.close(); }
}
const add = async (env, a, title, date, venue = '') => (await step(env, a, {post: '/api/add_work', body: {title, date, ...(venue ? {venue} : {})}})).body.work_key;
const merges = sqlite => sqlite.prepare('SELECT work_key, into_key FROM merges ORDER BY work_key').all().map(r => [r.work_key, r.into_key]);
const open = (env, a) => step(env, a, {get: '/api/screen/works'});

test('two visits of the same title are merged into the earliest record when the diary opens', async () => withUser(async (env, a, sqlite) => {
  const k1 = await add(env, a, '舞台 銀河鉄道の父', '2025-03-01');
  const k2 = await add(env, a, '舞台「銀河鉄道の父」', '2025-03-08');
  await add(env, a, '別の芝居', '2025-03-02');
  await open(env, a);
  assert.deepEqual(merges(sqlite), [[k2, k1]]);
  // 何度開いても同じ（書き直さない）
  await open(env, a);
  assert.equal(merges(sqlite).length, 1);
}));

test('a rating on one of them moves to the kept record; two different ratings are left apart', async () => withUser(async (env, a, sqlite) => {
  const k1 = await add(env, a, '夜の果て', '2025-01-01');
  const k2 = await add(env, a, '夜の果て', '2025-02-01');
  await step(env, a, {post: '/api/rate', body: {work_key: k2, verdict: '◎'}});
  await step(env, a, {get: '/api/screen/rate'});
  assert.deepEqual(merges(sqlite), [[k2, k1]]);
  assert.equal(sqlite.prepare('SELECT verdict FROM works WHERE work_key=?').get(k1).verdict, '◎');
  const k3 = await add(env, a, '朝の光', '2025-01-01');
  const k4 = await add(env, a, '朝の光', '2025-02-01');
  await step(env, a, {post: '/api/rate', body: {work_key: k3, verdict: '◎'}});
  await step(env, a, {post: '/api/rate', body: {work_key: k4, verdict: '×'}});
  await open(env, a);
  assert.ok(!merges(sqlite).some(([w]) => w === k3 || w === k4));
}));

test('the same title by another troupe at another theatre is another production', async () => withUser(async (env, a, sqlite) => {
  const ins = sqlite.prepare("INSERT INTO past_stage(stage_id,title,tkey,start,end,venue,grp,pref,people) VALUES(?,'ハムレット','ハムレット',?,?,?,?,'東京都','[]')");
  ins.run('9201', '2023-05-01', '2023-05-10', '劇場A', '劇団A');
  ins.run('9202', '2024-05-01', '2024-05-10', '劇場B', '劇団B');
  const k1 = await add(env, a, 'ハムレット', '2023-05-03', '劇場A');
  const k2 = await add(env, a, 'ハムレット', '2024-05-03', '劇場B');
  sqlite.prepare('UPDATE works SET stage_id=? WHERE work_key=?').run('9201', k1);
  sqlite.prepare('UPDATE works SET stage_id=? WHERE work_key=?').run('9202', k2);
  await open(env, a);
  assert.deepEqual(merges(sqlite), []);
}));

test('a merge the user took apart is not made again', async () => withUser(async (env, a, sqlite) => {
  const k1 = await add(env, a, '春の芝居', '2025-04-01');
  const k2 = await add(env, a, '春の芝居', '2025-04-05');
  await open(env, a);
  assert.deepEqual(merges(sqlite), [[k2, k1]]);
  assert.equal((await step(env, a, {post: '/api/merge_work', body: {work_key: k1, unmerge: true}})).status, 200);
  await open(env, a);
  assert.deepEqual(merges(sqlite), []);
}));
