// 観終わった公演に、もう一度「購入済」を付ける（起案者の指摘 2026-10-24「すでに観劇記録に入っているものを改めて購入済に
// いれても表示されない」）。観た回の券（過ぎた日）が残っていると、その日を「終わる日」と見て一覧から外していた。
// 観劇日の追加（起案者の指摘 2026-10-24「ミス・サイゴン1月の終わりまでツアーでやってるのに、観劇日を追加しようとしても
// 1月カレンダーが選べなくなってしまってる」）── 日付の範囲を、押した会場だけでなくツアー全体にする。
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

test('pressing 購入済 again after the seen day brings the production back to the list', async () => {
  const {env, sqlite} = tour();
  const a = await signIn(env);
  try {
    // 10/5 に観た（券があり、記録になっている）
    assert.equal((await owned(env, a, '101')).status, 200);
    assert.equal((await step(env, a, {post: '/api/ticket', body: {stage_id: '101', date: '2026-10-05', time: '13:00'}})).status, 200);
    assert.doesNotMatch(await tickets(env, a), /data-stage="101"/);   // 観た日が過ぎたので外れる（これまでどおり）
    assert.equal(sqlite.prepare("SELECT count(*) AS n FROM works WHERE stage_id='101'").get().n, 1);
    // 次の日に、もう一度観るために「購入済」を押す
    env.CLOCK = {today: '2026-10-13', now: Date.parse('2026-10-13T03:00:00Z')};
    assert.equal((await owned(env, a, '101')).status, 200);
    assert.match(await tickets(env, a), /data-stage="101"/);
  } finally { sqlite.close(); }
});

test('観劇日を追加: the date range covers the whole tour, not only the venue pressed', async () => {
  const {env, sqlite} = tour();
  const a = await signIn(env);
  try {
    assert.equal((await owned(env, a, '101')).status, 200);
    const html = (await step(env, a, {get: '/api/screen/calendar'})).body.body_html;
    assert.match(html, /<option value="10[12]" data-lo="2026-10-01" data-hi="2027-01-24">ミス・サイゴン（2 会場）/);
    // 1 月の日を入れると、その日に上演している会場（102）の券になる（これまでどおり、lists.ticketAction）
    const r = await step(env, a, {post: '/api/ticket', body: {stage_id: '101', date: '2027-01-20', time: ''}});
    assert.equal(r.body.stage_id, '102');
  } finally { sqlite.close(); }
});
