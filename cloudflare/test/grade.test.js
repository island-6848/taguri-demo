// 評価の段階: 初期設定は星 5 段階（"n/5"）、◎○△× で付けている人は ◎○△× のまま（screens/grade.js）。
// 起案者の指示（2026-10-14）「星5段階を初期設定にして。言葉の案は逆に決めないほうがいいんじゃない？」
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {setup, step, signIn} from './screens/harness.js';
import {gradeText, markOf, isTop, gradeButtons} from '../src/screens/grade.js';
import {gradeOf} from '../src/recommend.js';

test('star helpers: text, side, top, and the recommender reads n/5', () => {
  assert.equal(gradeText('4/5'), '★4');
  assert.equal(gradeText('◎'), '◎');
  assert.deepEqual(['5/5', '4/5', '3/5', '2/5', '1/5'].map(markOf), ['◎', '○', '', '△', '×']);
  assert.ok(isTop('5/5') && isTop('◎') && !isTop('4/5'));
  assert.deepEqual(gradeOf('3/5'), [3, 5]);
  // no words on the stars: each person's own scale (the recommender reads the place among their own ratings)
  assert.doesNotMatch(gradeButtons('stars'), /合って|とても|ふつう/);
  assert.equal((gradeButtons('stars').match(/<button/g) || []).length, 5);
});

test('a new user rates with stars; the saved n/5 shows as ★n and groups on the rate screen', async () => {
  const {env, sqlite} = setup();
  const a = await signIn(env);
  try {
    const k = (await step(env, a, {post: '/api/add_work', body: {title: '星で付ける舞台', date: '2026-08-01'}})).body.work_key;
    const unrated = (await step(env, a, {get: '/api/screen/unrated'})).body.body_html;
    assert.match(unrated, /data-v="1\/5"[^>]*>★1<\/button>.*data-v="5\/5"[^>]*>★5<\/button>/s);
    assert.doesNotMatch(unrated, /data-v="◎"/);
    assert.equal((await step(env, a, {post: '/api/rate', body: {work_key: k, verdict: '4/5'}})).status, 200);
    assert.equal(sqlite.prepare('SELECT verdict FROM works WHERE work_key=?').get(k).verdict, '4/5');
    const rate = (await step(env, a, {get: '/api/screen/rate'})).body.body_html;
    assert.match(rate, /星の数ごとに分けています/);
    assert.match(rate, /class="stamp" data-stamp="1"[^>]*>★4<\/span>/);
    assert.match(rate, /<td>★4<\/td>/);
    assert.equal((await step(env, a, {post: '/api/rate', body: {work_key: k, verdict: '6/5'}})).status, 400);
  } finally { sqlite.close(); }
});

test('a user who already rates with ◎○△× keeps ◎○△×', async () => {
  const {env, sqlite} = setup();
  const a = await signIn(env);
  try {
    const k = (await step(env, a, {post: '/api/add_work', body: {title: '記号で付けた舞台', date: '2026-08-01'}})).body.work_key;
    await step(env, a, {post: '/api/add_work', body: {title: 'まだの舞台', date: '2026-08-02'}});
    assert.equal((await step(env, a, {post: '/api/rate', body: {work_key: k, verdict: '◎'}})).status, 200);
    const unrated = (await step(env, a, {get: '/api/screen/unrated'})).body.body_html;
    assert.match(unrated, /<button data-v="◎">◎<\/button>/);
    assert.doesNotMatch(unrated, /★/);
  } finally { sqlite.close(); }
});
