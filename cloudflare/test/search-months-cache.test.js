// 探すの「月ごとの公演の数」は、誰が開いても同じなので 1 日 1 回だけ数える（issue #242。前は開くたびに
// これからの公演を全部読んでいた）。索引の版か日付が変われば数え直す
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {setup, signIn, step} from './screens/harness.js';

const COUNT_SQL = /SELECT stage_id, start, end FROM rec_stage/;
test('探す: 月ごとの数は 1 日 1 回だけ数え、2 回目からは rec_meta の控えを使う', async () => {
  const {env, sqlite} = setup();
  try {
    const a = await signIn(env);
    let counted = 0;
    const prepare = env.DB.prepare;
    env.DB.prepare = sql => { if (COUNT_SQL.test(sql)) counted += 1; return prepare(sql); };
    const first = (await step(env, a, {get: '/api/screen/search'})).body.body_html;
    assert.equal(counted, 1);
    const again = (await step(env, a, {get: '/api/screen/search?q=' + encodeURIComponent('劇団')})).body.body_html;
    assert.equal(counted, 1);
    assert.ok(sqlite.prepare("SELECT v FROM rec_meta WHERE k='search_months'").get());
    // 次の日は数え直す
    env.CLOCK = {...env.CLOCK, today: new Date(Date.parse(env.CLOCK.today) + 86400000).toISOString().slice(0, 10)};
    await step(env, a, {get: '/api/screen/search'});
    assert.equal(counted, 2);
    assert.ok(first.length && again.length);
  } finally { sqlite.close(); }
});
