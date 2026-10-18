// アカウントのページの「これまでの記録」（起案者の指示 2026-10-18「作品でまとめない単純に舞台観に行った回数『観た回数』のカウントも出して。
// 同箇所で『お気に入り』が常に0件なのなぜ？」）と、購入済みの公演を未評価に移す時刻（同じ日「観に行く日の公演開始時間過ぎてから」）
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {setup, step, signIn} from './screens/harness.js';
import {startPassed} from '../src/screens/lists.js';

test('観た回数 counts every visit, and お気に入り counts the registered names', async () => {
  const {env, sqlite} = setup();
  const a = await signIn(env);
  try {
    const k = (await step(env, a, {post: '/api/add_work', body: {title: 'Aの舞台', date: '2026-08-01'}})).body.work_key;
    sqlite.prepare('UPDATE works SET times=3 WHERE work_key=?').run(k);
    await step(env, a, {post: '/api/add_work', body: {title: 'Bの舞台', date: '2026-08-02'}});
    for (const [kind, name] of [['人', '俳優甲'], ['団体', '劇団乙']]) await step(env, a, {post: '/api/favourite', body: {action: 'add', kind, name}});
    const page = (await step(env, a, {get: '/api/screen/account'})).body.body_html;
    assert.match(page, /<b>2<\/b><span>観た作品/);
    assert.match(page, /<b>4<\/b><span>観た回数/);
    assert.match(page, /<b>2<\/b><span>お気に入り/);
  } finally { sqlite.close(); }
});

test('startPassed: the day before, the day after the start time (JST), and a day without a time waits for the next day', () => {
  // 2026-10-18 19:30 JST
  const ctx = {today: '2026-10-18', now: Date.parse('2026-10-18T10:30:00Z')};
  assert.equal(startPassed('2026-10-17', '', ctx), true);
  assert.equal(startPassed('2026-10-18', '19:00', ctx), true);
  assert.equal(startPassed('2026-10-18', '19:30', ctx), true);
  assert.equal(startPassed('2026-10-18', '20:00', ctx), false);
  assert.equal(startPassed('2026-10-18', '', ctx), false);
  assert.equal(startPassed('2026-10-19', '13:00', ctx), false);
  assert.equal(startPassed('', '', ctx), false);
});
