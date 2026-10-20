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

// よく観ている団体・よく行く劇場のランキング（起案者の指示 2026-10-20「ランキングぽいデザインに。劇場の方は、作品数と
// 単純に行った回数（同じ作品でも複数数える）で切り替えられるようにして」）
test('ranking: ties share a rank, and a tie across the cut stays in', async () => {
  const {ranking} = await import('../src/screens/account.js');
  const r = ranking(new Map([['甲', 3], ['乙', 2], ['丙', 2], ['丁', 1], ['戊', 1], ['己', 1], ['庚', 0]]), 4);
  assert.deepEqual(r.map(([v, n, k]) => `${k}:${v}${n}`), ['1:甲3', '2:乙2', '2:丙2', '4:己1', '4:丁1', '4:戊1']);
});

test('よく行く劇場 counts works and visits, switched without a script', async () => {
  const {env, sqlite} = setup();
  const a = await signIn(env);
  try {
    // 劇場A: 同じ作品を 2 日と、別の作品 1 本（3 回目は times=2）。劇場B: 1 作品を 1 回
    for (const [title, date, venue] of [['春の舞台', '2026-08-01', '劇場A'], ['春の舞台', '2026-08-05', '劇場A'],
      ['夏の舞台', '2026-08-10', '劇場A'], ['秋の舞台', '2026-08-20', '劇場B']]) {
      await step(env, a, {post: '/api/add_work', body: {title, date, venue}});
    }
    sqlite.prepare("UPDATE works SET times=2 WHERE title='夏の舞台'").run();
    const page = (await step(env, a, {get: '/api/screen/account'})).body.body_html;
    const list = cls => page.match(new RegExp(`<ol class="rk ${cls}">(.*?)</ol>`, 's'))[1];
    const rows = cls => [...list(cls).matchAll(/aria-label="(\d+) 位">\d+<\/b><span class="rk-name">([^<]+)<\/span>.*?<small>([^<]+)<\/small>/g)].map(m => `${m[1]}:${m[2]}:${m[3]}`);
    assert.deepEqual(rows('rk-works'), ['1:劇場A:2 作品', '2:劇場B:1 作品']);
    assert.deepEqual(rows('rk-visits'), ['1:劇場A:4 回', '2:劇場B:1 回']);
    assert.match(page, /<input type="radio" name="rk-venue" id="rk-v-works" value="works" checked><label for="rk-v-works">作品数<\/label>/);
    assert.match(page, /<label for="rk-v-visits">行った回数<\/label>/);
    // 1 位の札は色つき、棒は 1 位を満たん
    assert.match(list('rk-works'), /<li class="rk-1"><b class="rk-no"[^>]*>1<\/b>.*?width:100%/s);
  } finally { sqlite.close(); }
});
