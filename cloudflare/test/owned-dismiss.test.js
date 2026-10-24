// 購入済の公演を、カード右上の ✕ で一覧から外す（起案者の指示 2026-10-24「購入済にある公演、もう1回行ったし今後もチケット
// 買い足さなさそうなやつはカード右上の✕ボタンを押して画面から消せるようにしたい」）。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {setup, step, signIn} from './screens/harness.js';

const here = p => new URL(p, import.meta.url).pathname;
const FIXTURE = JSON.parse(execFileSync('python3', [here('./screens/recommend_fixture.py')], {encoding: 'utf8', maxBuffer: 64 * 1024 * 1024}));

test('a 購入済 card carries its tour venues, so ✕ (dismiss with them) takes it off the list and keeps the records', async () => {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  sqlite.exec("UPDATE rec_card SET tour='T1' WHERE stage_id IN ('101','102')");
  for (const t of ['rec_card', 'rec_stage']) {
    sqlite.exec(`UPDATE ${t} SET start='2026-10-01', end='2026-11-10' WHERE stage_id='101'`);
    sqlite.exec(`UPDATE ${t} SET start='2026-12-01', end='2026-12-10' WHERE stage_id='102'`);
  }
  const a = await signIn(env);
  try {
    await step(env, a, {post: '/api/react', body: {stage_id: '101', value: 'owned', nofill: true, siblings: ['102']}});
    // 行く日を入れずに購入済にした公演は、会期の終わりまで一覧に残る（今日 10/12 は会期中）
    await step(env, a, {post: '/api/add_work', body: {title: '舞台ひとつめ', date: '2026-10-05', stage_id: '101'}});
    const html = (await step(env, a, {get: '/api/screen/tickets'})).body.body_html;
    const tours = /<article class="ticket owned" data-stage="101" data-tours="([^"]*)"/.exec(html);
    assert.ok(tours, 'the card is listed');
    assert.equal(tours[1], '102');
    // app.js の ✕ は data-tours を siblings にして 'dismiss' を送る
    assert.equal((await step(env, a, {post: '/api/react', body: {stage_id: '101', value: 'dismiss', nofill: true, siblings: tours[1].split(',')}})).status, 200);
    assert.doesNotMatch((await step(env, a, {get: '/api/screen/tickets'})).body.body_html, /data-stage="10[12]"/);
    assert.equal(sqlite.prepare("SELECT count(*) AS n FROM works WHERE stage_id='101'").get().n, 1);
  } finally { sqlite.close(); }
});
