// 購入済の公演は、入れた日（行く日・観た記録の日）のうちいちばん遅い日を過ぎたら、ツアー中でも一覧から外す。
// 観劇記録を追加などで先の日が入れば、また出す（起案者の指示 2026-10-24「購入済の公演、登録日が過ぎたらツアー中でも一覧からは
// 消してよい（代わりに、+ボタンなどから記録が追加されたら再表示）」）。✕ で外したあと「元に戻す」（購入済を押し直す）と、
// 前に入れた先の行く日で終わる（起案者の指示 2026-10-24「間違って✕ボタンで消してしまったら戻せるようにして」）
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {setup, step, signIn} from './screens/harness.js';

const here = p => new URL(p, import.meta.url).pathname;
const FIXTURE = JSON.parse(execFileSync('python3', [here('./screens/recommend_fixture.py')], {encoding: 'utf8', maxBuffer: 64 * 1024 * 1024}));
function tour() {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  // 101（10/1〜11/10、今日 10/12 は会期中）と 102（12/1〜1/24）を 1 つのツアーにする
  sqlite.exec("UPDATE rec_card SET tour='T1' WHERE stage_id IN ('101','102')");
  // 同じ題名のツアー（会場ごとに公演が分かれる）
  for (const t of ['rec_card', 'rec_stage']) {
    sqlite.exec(`UPDATE ${t} SET title='ミス・サイゴン', start='2026-10-01', end='2026-11-10' WHERE stage_id='101'`);
    sqlite.exec(`UPDATE ${t} SET title='ミス・サイゴン', start='2026-12-01', end='2027-01-24' WHERE stage_id='102'`);
  }
  sqlite.exec("UPDATE rec_stage SET entry=json_set(entry,'$.period','2026/10/01 ～ 2026/11/10') WHERE stage_id='101'");
  sqlite.exec("UPDATE rec_stage SET entry=json_set(entry,'$.period','2026/12/01 ～ 2027/01/24') WHERE stage_id='102'");
  sqlite.exec("DELETE FROM catalogue WHERE id IN ('101','102')");
  return {env, sqlite};
}
const owned = (env, a, sid) => step(env, a, {post: '/api/react', body: {stage_id: sid, value: 'owned', nofill: true, siblings: []}});
const tickets = async (env, a) => (await step(env, a, {get: '/api/screen/tickets'})).body.body_html;


test('a recorded day ends the production on 購入済 even while the tour goes on; a later day brings it back', async () => {
  const {env, sqlite} = tour();
  const a = await signIn(env);
  try {
    env.CLOCK = {today: '2026-10-01', now: Date.parse('2026-10-01T03:00:00Z')};
    assert.equal((await owned(env, a, '101')).status, 200);
    env.CLOCK = {today: '2026-10-12', now: Date.parse('2026-10-12T03:00:00Z')};
    assert.match(await tickets(env, a), /data-stage="101"/);            // 日を入れていなければ、ツアーの終わり（1/24）まで出す
    // ＋（観劇記録を追加）で、10/10 に観た記録を入れる
    assert.equal((await step(env, a, {post: '/api/add_work', body: {title: 'ミス・サイゴン', date: '2026-10-10', venue: '', time: '', stage_id: '101'}})).status, 200);
    assert.doesNotMatch(await tickets(env, a), /data-stage="10[12]"/);   // 入れた日が過ぎたので外す（ツアーは 1/24 まで）
    // もう一度、12/5 に行く日を足すと、また出す
    assert.equal((await step(env, a, {post: '/api/add_work', body: {title: 'ミス・サイゴン', date: '2026-12-05', venue: '', time: '', stage_id: '102'}})).status, 200);
    assert.match(await tickets(env, a), /data-stage="10[12]"/);
  } finally { sqlite.close(); }
});

test('undoing ✕ on 購入済 (pressing 購入済 again) keeps the ticket entered before', async () => {
  const {env, sqlite} = tour();
  const a = await signIn(env);
  try {
    assert.equal((await owned(env, a, '101')).status, 200);
    assert.equal((await step(env, a, {post: '/api/ticket', body: {stage_id: '101', date: '2026-11-03', time: '14:00'}})).status, 200);
    assert.equal((await step(env, a, {post: '/api/react', body: {stage_id: '101', value: 'dismiss', nofill: true, siblings: ['102']}})).status, 200);
    assert.doesNotMatch(await tickets(env, a), /data-stage="10[12]"/);
    env.CLOCK = {today: '2026-10-12', now: Date.parse('2026-10-12T05:00:00Z')};
    assert.equal((await step(env, a, {post: '/api/react', body: {stage_id: '101', value: 'owned', nofill: true, siblings: ['102']}})).status, 200);
    assert.match(await tickets(env, a), /data-stage="101"/);
    // 11/3 の開演を過ぎたら外れる（ツアーの終わりまで残らない）
    env.CLOCK = {today: '2026-11-03', now: Date.parse('2026-11-03T06:00:00Z')};
    assert.doesNotMatch(await tickets(env, a), /data-stage="10[12]"/);
  } finally { sqlite.close(); }
});
