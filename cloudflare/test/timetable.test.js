// 観劇の時間割（起案者の指示 2026-10-16「時間割から実装してよい」、dec-records-viz-picks）。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {weekday, slotOf, visits, timetablePanel} from '../src/screens/timetable.js';
import {setup, step, signIn} from './screens/harness.js';

test('weekday and matinée / soirée', () => {
  assert.equal(weekday('2026-10-16'), 4);          // 金
  assert.equal(weekday('2026-10-18'), 6);          // 日
  assert.equal(weekday('2026-10-19'), 0);          // 月
  assert.equal(weekday('2026-13-01'), null);
  assert.equal(slotOf('13:00'), 'm');
  assert.equal(slotOf('14:59'), 'm');
  assert.equal(slotOf('15:00'), 'j');
  assert.equal(slotOf('16:59'), 'j');
  assert.equal(slotOf('17:00'), 's');
  assert.equal(slotOf('19:30'), 's');
  assert.equal(slotOf(''), 'u');
});

test('a ticket is a visit; a work adds only the days no ticket stands for; the future does not count', () => {
  const vs = visits(
    [{date: '2026-10-10', time: '13:00'}, {date: '2026-10-11', time: '18:30'}, {date: '2026-12-01', time: '13:00'}],
    [{first_date: '2026-10-10', last_date: '2026-10-12', time: '14:00'}, {first_date: '2026-09-05', last_date: '2026-09-05', time: ''}],
    '2026-10-16');
  assert.deepEqual(vs.map(v => v.date + ' ' + v.time).sort(), ['2026-09-05 ', '2026-10-10 13:00', '2026-10-11 18:30', '2026-10-12 ']);
});

test('the panel counts each weekday and slot and writes every number', () => {
  const html = timetablePanel([
    {date: '2026-10-10', time: '13:00'}, {date: '2026-10-03', time: '12:00'},   // 土 マチネ ×2
    {date: '2026-10-08', time: '19:00'},                                        // 木 ソワレ
    {date: '2026-10-11', time: '15:30'},                                        // 日 ジュルネ
    {date: '2026-10-05', time: ''}]);                                            // 月 時刻なし
  // 図の上の説明の文は出さない（起案者の指示 2026-10-24）
  assert.doesNotMatch(html, /いちばん多いのは|開演時刻が分かるのは|<p class="lead">/);
  assert.match(html, /<th scope="col" title="開演時刻が分からない回">時刻なし<\/th>/);
  assert.match(html, /<th scope="col" title="15 時から 17 時より前">ジュルネ<\/th>/);
  assert.match(html, /title="日曜 ジュルネ：1 回"><span class="tt-n">1<\/span>/);
  assert.match(html, /<th scope="row">土<\/th><td class="tt-c tt-4" title="土曜 マチネ：2 回"><span class="tt-n">2<\/span>/);
  assert.match(html, /<td class="tt-c tt-0" title="火曜 マチネ：0 回"><span class="tt-n">·<\/span>/);
  assert.equal(timetablePanel([]), '');
});

test('the 時刻なし column is left out when every visit has a time', () => {
  // 起案者の指示 2026-10-24「時刻なしの列は1件もなければ非表示」
  const html = timetablePanel([{date: '2026-10-10', time: '13:00'}, {date: '2026-10-08', time: '19:00'}]);
  assert.doesNotMatch(html, /時刻なし/);
  assert.match(html, /<thead><tr><th><\/th><th scope="col"[^>]*>マチネ<\/th><th scope="col"[^>]*>ジュルネ<\/th><th scope="col"[^>]*>ソワレ<\/th><th scope="col">計<\/th><\/tr><\/thead>/);
  assert.match(html, /<th scope="row">土<\/th><td class="tt-c tt-4" title="土曜 マチネ：1 回">[^]*?<td class="tt-t">1<\/td><\/tr>/);
});

test('眺める shows the timetable from the diary and the tickets', async () => {
  const {env, sqlite} = setup();
  const a = await signIn(env);
  try {
    const key = (await step(env, a, {post: '/api/add_work', body: {title: '観た舞台', date: '2026-08-08'}})).body.work_key;
    assert.ok(key);
    const html = (await step(env, a, {get: '/api/screen/records'})).body.body_html;
    assert.match(html, /観劇の時間割/);
    // 2026-08-08 is a Saturday.
    assert.match(html, /<th scope="row">土<\/th>[^]*?時刻なし：1 回/);
  } finally { sqlite.close(); }
});
