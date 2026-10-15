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
  assert.doesNotMatch(gradeButtons('stars5'), /合って|とても|ふつう/);
  assert.equal((gradeButtons('stars5').match(/<button/g) || []).length, 5);
});

test('a new user rates with stars; the saved n/5 shows as ★n and groups on the rate screen', async () => {
  const {env, sqlite} = setup();
  const a = await signIn(env);
  try {
    const k = (await step(env, a, {post: '/api/add_work', body: {title: '星で付ける舞台', date: '2026-08-01'}})).body.work_key;
    const unrated = (await step(env, a, {get: '/api/screen/unrated'})).body.body_html;
    assert.match(unrated, /<button class="star" data-v="1\/5" aria-label="星 1"><\/button>.*<button class="star" data-v="5\/5" aria-label="星 5"><\/button>/s);
    assert.doesNotMatch(unrated, /data-v="◎"/);
    assert.equal((await step(env, a, {post: '/api/rate', body: {work_key: k, verdict: '4/5'}})).status, 200);
    assert.equal(sqlite.prepare('SELECT verdict FROM works WHERE work_key=?').get(k).verdict, '4/5');
    const rate = (await step(env, a, {get: '/api/screen/rate'})).body.body_html;
    assert.match(rate, /星の数ごとに分けています/);
    assert.match(rate, /class="stamp" data-stamp="1"[^>]*>★4<\/span>/);
    assert.match(rate, /<td>★4<\/td>/);
    // the stars up to the rating are filled (★★★★☆) when the rating is opened again
    assert.match(rate, /(<button class="star on" data-v="[1-4]\/5"[^>]*><\/button>){4}<button class="star" data-v="5\/5"/);
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

test('scale helpers: ○× and ○△× show as shapes, 0.5 steps as ★n.5, sides and the top by place', () => {
  assert.deepEqual(['2/2', '1/2', '3/3', '2/3', '1/3'].map(gradeText), ['○', '×', '○', '△', '×']);
  assert.deepEqual(['1/11', '8/11', '11/11'].map(gradeText), ['★0', '★3.5', '★5']);
  assert.deepEqual(['11/11', '8/11', '6/11', '4/11', '1/11'].map(markOf), ['◎', '○', '', '△', '×']);
  assert.ok(isTop('2/2') && isTop('3/3') && isTop('11/11') && !isTop('10/11'));
  assert.equal(gradeButtons('marks2'), '<button data-v="2/2">○</button><button data-v="1/2">×</button>');
  assert.match(gradeButtons('stars11', '8/11'), /<button class="star0" data-v="1\/11"[^>]*>0<\/button>(<span class="hs on">.*?<\/span>){3}<span class="hs h">/);
  assert.deepEqual(gradeOf('8/11'), [8, 11]);
});

test('the scale is chosen on 設定; old ratings keep their own scale', async () => {
  const {env, sqlite} = setup();
  const a = await signIn(env);
  try {
    const k1 = (await step(env, a, {post: '/api/add_work', body: {title: '星で付けた舞台', date: '2026-08-01'}})).body.work_key;
    const k2 = (await step(env, a, {post: '/api/add_work', body: {title: '記号で付ける舞台', date: '2026-08-02'}})).body.work_key;
    await step(env, a, {post: '/api/rate', body: {work_key: k1, verdict: '5/5'}});
    const settings = (await step(env, a, {get: '/api/screen/settings'})).body.body_html;
    assert.match(settings, /評価の付け方/);
    assert.match(settings, /<input type="radio" name="rscale" value="stars5" checked>/);
    assert.equal((await step(env, a, {post: '/api/rating_scale', body: {scale: 'bogus'}})).status, 400);
    assert.equal((await step(env, a, {post: '/api/rating_scale', body: {scale: 'marks3'}})).status, 200);
    const unrated = (await step(env, a, {get: '/api/screen/unrated'})).body.body_html;
    assert.match(unrated, /<button data-v="3\/3">○<\/button><button data-v="2\/3">△<\/button><button data-v="1\/3">×<\/button>/);
    assert.equal((await step(env, a, {post: '/api/rate', body: {work_key: k2, verdict: '2/3'}})).status, 200);
    assert.equal((await step(env, a, {post: '/api/rate', body: {work_key: k2, verdict: '4/3'}})).status, 400);
    const rate = (await step(env, a, {get: '/api/screen/rate?v=all'})).body.body_html;
    assert.match(rate, /data-stamp="1"[^>]*>★5<\/span>/);       // the old star rating stays a star
    assert.match(rate, /data-stamp="1"[^>]*>△<\/span>/);
    assert.match(rate, /<tr data-v="2\/3"><td>△<\/td>/);
    await step(env, a, {post: '/api/rating_scale', body: {scale: 'stars11'}});
    assert.match((await step(env, a, {get: '/api/screen/rate?v=all'})).body.body_html, /class="star0/);
  } finally { sqlite.close(); }
});
