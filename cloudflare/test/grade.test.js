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
  assert.equal((gradeButtons('stars5').match(/<button class="star/g) || []).length, 5);
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
    // 星の行には余白の丸い判子を出さず、星の列を常に出す（起案者 2026-10-15「下に星で表示されるんなら、〇の枠いらなくない？」）
    assert.doesNotMatch(rate, /data-stamp="1"/);
    assert.doesNotMatch(rate, /data-rate-open/);
    assert.match(rate, /<div class="dbar" data-rows="\[\[&quot;★4&quot;,1\]\]">/);   // 評価の分布の段階と件数（「数字で見る」の表は 2026-10-24 にやめた）
    // the stars up to the rating are filled (★★★★☆) when the rating is opened again
    assert.match(rate, /(<button class="star on" data-v="[1-4]\/5"[^>]*><\/button>){4}<button class="star" data-v="5\/5"/);
    assert.equal((await step(env, a, {post: '/api/rate', body: {work_key: k, verdict: '6/5'}})).status, 400);
    // 図形の段階では判子のまま
    await step(env, a, {post: '/api/rating_scale', body: {scale: 'marks4'}});
    assert.match((await step(env, a, {get: '/api/screen/rate'})).body.body_html, /class="stamp" data-stamp="1"[^>]*>★4<\/span>/);
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
  assert.match(gradeButtons('stars11', '8/11'), /^(<span class="hs on">.*?<\/span>){3}<span class="hs h">/);
  // 星 0 の押し口はやめた（起案者の指示 2026-10-16）。そのあと置いた「評価しない」も、星の右端の ✕（評価を消して未評価に戻す）に
  // 替えた（起案者の指示 2026-10-18「『評価しない』のボタンじゃなくて、星の右端に✕ボタンをつけることでnullにできるようにして」）。
  // ✕ は評価が付いているときだけ出す（前の「評価しない」＝まだ判断できない を付けた行にも出す）
  assert.doesNotMatch(gradeButtons('stars11'), /star0|data-v="1\/11"|nograde|評価しない/);
  const X = /<button type="button" class="gclr" data-clear="1" aria-label="評価を消す（未評価に戻す）" title="評価を消す"( hidden)?>✕<\/button>$/;
  assert.equal(X.exec(gradeButtons('stars11'))?.[1], ' hidden');
  assert.equal(X.exec(gradeButtons('stars5'))?.[1], ' hidden');
  assert.equal(X.exec(gradeButtons('stars5', '4/5'))?.[1], undefined);
  assert.equal(X.exec(gradeButtons('stars11', '8/11'))?.[1], undefined);
  assert.equal(X.exec(gradeButtons('stars5', 'まだ判断できない'))?.[1], undefined);
  assert.doesNotMatch(gradeButtons('marks4', '◎'), /gclr/);
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
    assert.match(rate, /data-stamp="1"[^>]*>★5<\/span>/);       // the old star rating stays a star (a stamp: the buttons are ○△× now)
    assert.match(rate, /data-stamp="1"[^>]*>△<\/span>/);
    assert.match(rate, /data-rows="[^"]*&quot;△&quot;,1/);
    await step(env, a, {post: '/api/rating_scale', body: {scale: 'stars11'}});
    assert.match((await step(env, a, {get: '/api/screen/rate?v=all'})).body.body_html, /class="gclr"/);
  } finally { sqlite.close(); }
});

// 星の右端の ✕ で評価を消す（起案者の指示 2026-10-18「『評価しない』のボタンじゃなくて、星の右端に✕ボタンをつけることで
// nullにできるようにして」）。POST /api/rate {work_key, clear: true} で verdict は NULL（未評価）に戻り、詳細は残る
test('the ✕ after the stars clears a rating back to unrated and keeps the 詳細', async () => {
  const {env, sqlite} = setup();
  const a = await signIn(env);
  try {
    const k = (await step(env, a, {post: '/api/add_work', body: {title: '消す舞台', date: '2026-08-01'}})).body.work_key;
    await step(env, a, {post: '/api/rate', body: {work_key: k, verdict: '4/5'}});
    await step(env, a, {post: '/api/rate', body: {work_key: k, aspects: ['++acting', '~music']}});
    const row = () => sqlite.prepare('SELECT verdict, aspects, rated_at FROM works WHERE work_key=?').get(k);
    assert.ok(row().rated_at);
    assert.match((await step(env, a, {get: '/api/screen/rate?v=all'})).body.body_html, /<button class="star on" data-v="4\/5"[^>]*><\/button><button class="star" data-v="5\/5"[^>]*><\/button><button type="button" class="gclr" data-clear="1"[^>]*title="評価を消す">✕<\/button>/);
    const r = await step(env, a, {post: '/api/rate', body: {work_key: k, clear: true}});
    assert.equal(r.status, 200);
    assert.equal(r.body.verdict, null);
    assert.equal(row().verdict, null);
    assert.equal(row().aspects, '++acting,~music');
    const unrated = (await step(env, a, {get: '/api/screen/unrated'})).body.body_html;
    assert.match(unrated, /未評価 ── 1 件/);
    assert.match(unrated, /<button type="button" class="gclr" data-clear="1"[^>]*hidden>✕<\/button>/);
    assert.doesNotMatch(unrated, /class="star on"/);
    // 前に付けた「評価しない」（まだ判断できない）も読めて、✕ で消せる
    await step(env, a, {post: '/api/rate', body: {work_key: k, verdict: 'まだ判断できない'}});
    assert.match((await step(env, a, {get: '/api/screen/rate?v=all'})).body.body_html, /class="gclr" data-clear="1"[^>]*title="評価を消す">✕/);
    assert.equal((await step(env, a, {post: '/api/rate', body: {work_key: k, clear: true}})).status, 200);
    assert.equal(row().verdict, null);
    // clear は true だけ。ほかの値や無い作品は断る
    assert.equal((await step(env, a, {post: '/api/rate', body: {work_key: k, clear: 1}})).status, 400);
    assert.equal((await step(env, a, {post: '/api/rate', body: {work_key: '無い#2026-01-01', clear: true}})).status, 400);
  } finally { sqlite.close(); }
});

// 尺度を途中で変えても、同じ星の数は評価一覧の 1 つのタブ・分布の 1 本（起案者の指摘 2026-10-20「星５がタブ２個に分かれて表示されてる」）
test('sameGrade: ★n of the 5-step scale is the same value as ★n of the 0.5-step scale', async () => {
  const {sameGrade, gradeText} = await import('../src/screens/grade.js');
  assert.equal(sameGrade('5/5'), '11/11');
  assert.equal(sameGrade('1/5'), '3/11');
  assert.equal(sameGrade('9/11'), '9/11');
  assert.equal(sameGrade('◎'), '◎');
  for (const n of [1, 2, 3, 4, 5]) assert.equal(gradeText(sameGrade(`${n}/5`)), gradeText(`${n}/5`));
  const {setup, step, signIn} = await import('./screens/harness.js');
  const {env, sqlite} = setup();
  const a = await signIn(env);
  try {
    for (const [t, v] of [['甲の舞台', '5/5'], ['乙の舞台', '11/11'], ['丙の舞台', '4/5']]) {
      const key = (await step(env, a, {post: '/api/add_work', body: {title: t, date: '2026-05-01'}})).body.work_key;
      assert.equal((await step(env, a, {post: '/api/rate', body: {work_key: key, verdict: v}})).status, 200);
    }
    const html = (await step(env, a, {get: '/api/screen/rate'})).body.body_html;
    const tabs = [...html.matchAll(/>(★[\d.]+)[^<]*<span class="mn">(\d+)<\/span>/g)].map(m => m[1] + ':' + m[2]);
    assert.deepEqual(tabs, ['★5:2', '★4:1']);
    assert.equal((html.match(/&quot;★5&quot;/g) || []).length, 1);
  } finally { sqlite.close(); }
});
