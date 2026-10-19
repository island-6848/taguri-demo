// 観劇記録の追加で選んだ公演の開演時刻（起案者の指示 2026-10-19「観た日の時間、も最初からわかってるならその時間しか選べないように
// プルダウン化してよい」、suggest.stageTimes）
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {setup, step, signIn} from './screens/harness.js';

const here = p => new URL(p, import.meta.url).pathname;
const FIXTURE = JSON.parse(execFileSync('python3', [here('./screens/recommend_fixture.py')], {encoding: 'utf8', maxBuffer: 64 * 1024 * 1024}));

test('the times of each day come from the timetable; 貸切 is left out; unknown stages give none', async () => {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  // 公演日時は管理者が直した分（stage_override の info.fields）として重ねる（e2e-walk と同じ）
  sqlite.prepare('INSERT INTO stage_override(stage_id,synopsis,themes,info,updated_at) VALUES(?,?,?,?,?)').run('101', null, null,
    JSON.stringify({fields: {'タイムテーブル': '11月1日(日) 13:00\n11月2日(月) 19:00\n11月3日(火) 13:00/18:00貸切'}}), '2026-10-18T00:00:00Z');
  const a = await signIn(env);
  try {
    const r = await step(env, a, {get: '/api/stage_times?stage_id=101'});
    assert.equal(r.status, 200);
    assert.deepEqual(r.body.times['2026-11-01'], ['13:00']);
    assert.deepEqual(r.body.times['2026-11-03'], ['13:00']);   // (貸)18:00 は入れない
    assert.equal(r.body.times['2026-11-04'], undefined);        // 休演
    assert.deepEqual((await step(env, a, {get: '/api/stage_times?stage_id=999999'})).body.times, {});
    assert.deepEqual((await step(env, a, {get: '/api/stage_times?stage_id=' + encodeURIComponent("1' OR 1")})).body.times, {});
  } finally { sqlite.close(); }
});
