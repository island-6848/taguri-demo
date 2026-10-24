// 購入済の公演と、ツアーのほかの会場（起案者の指摘 2026-10-24「『購入済みの公演』に観終わった公演の別のツアーの日程があったら、
// 再び出るようになってしまっている。そのツアー日程を購入済に登録していないのであれば、この画面に出さないようにして」）。
// ツアーのカードで「購入済」を押すと、同じ答えがほかの会場にも写る（source が '…_tour'）。写しは「買った」印ではない。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {setup, step, signIn} from './screens/harness.js';

const here = p => new URL(p, import.meta.url).pathname;
const FIXTURE = JSON.parse(execFileSync('python3', [here('./screens/recommend_fixture.py')], {encoding: 'utf8', maxBuffer: 64 * 1024 * 1024}));
function tourOfTwo() {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  // 102（10/1〜10/5、今日 10/12 には終わっている）と 101（11/1〜11/10、これから）を 1 つのツアーにする
  sqlite.exec("UPDATE rec_card SET tour='T1' WHERE stage_id IN ('101','102')");
  for (const t of ['rec_card', 'rec_stage']) {
    sqlite.exec(`UPDATE ${t} SET start='2026-10-01', end='2026-10-05' WHERE stage_id='102'`);
    sqlite.exec(`UPDATE ${t} SET start='2026-11-01', end='2026-11-10' WHERE stage_id='101'`);
  }
  return {env, sqlite};
}
const owned = (env, a, sid, siblings) => step(env, a, {post: '/api/react', body: {stage_id: sid, value: 'owned', nofill: true, siblings}});
const tickets = async (env, a) => (await step(env, a, {get: '/api/screen/tickets'})).body.body_html;
const worksOf = (sqlite, sid) => sqlite.prepare('SELECT count(*) AS n FROM works WHERE stage_id=?').get(sid).n;

test('a tour venue that only got the copied 購入済 does not bring the seen production back', async () => {
  const {env, sqlite} = tourOfTwo();
  const a = await signIn(env);
  try {
    assert.equal((await owned(env, a, '102', ['101'])).status, 200);
    assert.match(sqlite.prepare("SELECT source FROM reaction WHERE stage_id='101'").get().source, /_tour$/);
    // 102 は終わったので、購入済の一覧から外れ、記録（評価待ち）になる。写しだけの 101 の日程で出直さない
    const html = await tickets(env, a);
    assert.doesNotMatch(html, /data-stage="10[12]"/);
    assert.equal(worksOf(sqlite, '102'), 1);
    // 101 の会期も過ぎたあと、写しだけの 101 を「観た」記録にしない
    env.CLOCK = {today: '2026-11-20', now: Date.parse('2026-11-20T03:00:00Z')};
    await tickets(env, a);
    assert.equal(worksOf(sqlite, '101'), 0);
  } finally { sqlite.close(); }
});

test('the venue pressed 購入済 itself, or one with a ticket date, still shows until it is over', async () => {
  const {env, sqlite} = tourOfTwo();
  const a = await signIn(env);
  try {
    // これからの 101 で押した: 出る
    assert.equal((await owned(env, a, '101', ['102'])).status, 200);
    assert.match(await tickets(env, a), /data-stage="101"/);
  } finally { sqlite.close(); }
});
