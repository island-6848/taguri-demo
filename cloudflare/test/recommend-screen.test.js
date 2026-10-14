// 今週のおすすめ on the Worker (screens/recommend.js): the ranking from the user's own
// works, the cards rendered by the Python batch (build_cards.py) with the rank, the
// reasons and the poster filled in, the prefecture filter, and the three-choice writes.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {setup, step, signIn} from './screens/harness.js';

const here = p => new URL(p, import.meta.url).pathname;
const FIXTURE = JSON.parse(execFileSync('python3', [here('./screens/recommend_fixture.py')], {encoding: 'utf8', maxBuffer: 64 * 1024 * 1024}));

async function withIndex() {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  return {env, sqlite};
}
async function rateSeen(env, cookie, title, date, sid, verdict) {
  const key = (await step(env, cookie, {post: '/api/add_work', body: {title, date}})).body.work_key;
  assert.equal((await step(env, cookie, {post: '/api/link_stage', body: {work_key: key, stage_id: sid}})).status, 200);
  assert.equal((await step(env, cookie, {post: '/api/rate', body: {work_key: key, verdict}})).status, 200);
  return key;
}

test('a new account gets no recommendations and is told what to do', async () => {
  const {env, sqlite} = await withIndex();
  const a = await signIn(env);
  try {
    const got = await step(env, a, {get: '/api/screen/recommend'});
    assert.equal(got.status, 200);
    assert.equal(got.body.title, '今週のおすすめ');
    assert.equal(got.body.moving, undefined);
    assert.match(got.body.body_html, /<h1>今週のおすすめはありません<\/h1>/);
    assert.doesNotMatch(got.body.body_html, /<article/);
  } finally { sqlite.close(); }
});

test('a ◎ on a stage recommends the coming stage of the same people, with the Python card and the reasons', async () => {
  const {env, sqlite} = await withIndex();
  const a = await signIn(env), b = await signIn(env);
  try {
    await rateSeen(env, a, '終わった舞台', '2026-08-05', '103', '◎');
    await rateSeen(env, a, '一日だけの舞台', '2026-09-05', '104', '×');
    const html = (await step(env, a, {get: '/api/screen/recommend'})).body.body_html;
    assert.match(html, /<h1>今週のおすすめ 1 件<\/h1>/);
    assert.match(html, /<article class="ticket recommend" data-stage="101"/);
    assert.match(html, /<span class="sn">No\.01<\/span>/);
    assert.match(html, /<li class="rs b"><span class="net">人物<\/span>出演 <b>俳優甲<\/b><span class="n">（『終わった舞台』）<\/span>/);
    assert.doesNotMatch(html, /<!--(rank|why|poster)-->/);
    assert.match(html, /<button data-v="interest">興味あり<\/button>/);
    // The other user sees none of it.
    assert.doesNotMatch((await step(env, b, {get: '/api/screen/recommend'})).body.body_html, /<article/);
    // Prefecture filter: saved with ?f=1, applied on the next visit, cleared by an empty ?f=1.
    const osaka = (await step(env, a, {get: '/api/screen/recommend?f=1&pref=' + encodeURIComponent('大阪府')})).body.body_html;
    assert.match(osaka, /<h1>大阪府のおすすめはありません<\/h1>/);
    assert.match((await step(env, a, {get: '/api/screen/recommend'})).body.body_html, /いまは<b>大阪府（1 県）<\/b>/);
    const tokyo = (await step(env, a, {get: '/api/screen/recommend?f=1&pref=' + encodeURIComponent('東京都')})).body.body_html;
    assert.match(tokyo, /<h1>東京都のおすすめ 1 件<\/h1>/);
    assert.match((await step(env, a, {get: '/api/screen/recommend?f=1'})).body.body_html, /いまは<b>全国<\/b>/);
    // A poster in R2 goes into the card.
    sqlite.exec("INSERT INTO poster(stage_id,file) VALUES('101','101.webp')");
    sqlite.exec("UPDATE rec_cache SET stamp='x'");
    assert.match((await step(env, a, {get: '/api/screen/recommend'})).body.body_html, /<img class="poster" src="\/img\/101\.webp\?t=/);
  } finally { sqlite.close(); }
});

test('answering a card takes it out of the recommendations, for this user only', async () => {
  const {env, sqlite} = await withIndex();
  const a = await signIn(env), b = await signIn(env);
  try {
    for (const u of [a, b]) {
      await rateSeen(env, u, '終わった舞台', '2026-08-05', '103', '◎');
      await rateSeen(env, u, '一日だけの舞台', '2026-09-05', '104', '×');
    }
    const got = await step(env, a, {post: '/api/react', body: {stage_id: '101', value: 'interest', nofill: true, siblings: []}});
    assert.equal(got.status, 200);
    assert.deepEqual({ok: got.body.ok, value: got.body.value, fill: got.body.fill}, {ok: true, value: 'interest', fill: undefined});
    const fill = await step(env, a, {post: '/api/react', body: {stage_id: '101', fill_only: true, shown: ['101']}});
    assert.equal(fill.body.fill.html, '');
    assert.match(fill.body.fill.said, /入れ替える候補はもうありません/);
    assert.match((await step(env, a, {get: '/api/screen/recommend'})).body.body_html, /<h1>今週のおすすめはありません<\/h1>/);
    assert.match((await step(env, b, {get: '/api/screen/recommend'})).body.body_html, /data-stage="101"/);
    // A note alone is saved without answering; bad input is refused.
    assert.equal((await step(env, b, {post: '/api/react', body: {stage_id: '101', note: '俳優甲が観たい'}})).status, 200);
    assert.match((await step(env, b, {get: '/api/screen/recommend'})).body.body_html, /data-stage="101"/);
    assert.equal((await step(env, b, {post: '/api/react', body: {stage_id: '101', value: 'maybe'}})).status, 400);
    assert.equal((await step(env, b, {post: '/api/react', body: {stage_id: '../x', value: 'interest'}})).status, 400);
    const rows = sqlite.prepare("SELECT user_id, stage_id, interest, note FROM reaction ORDER BY user_id").all().map(r => ({...r}));
    assert.equal(rows.length, 2);
  } finally { sqlite.close(); }
});

// 2026-10-14「おすすめの画面を移して」: the 効かせ方 sliders (app.weight_form, /api/weight).
test('効かせ方: the sliders show the saved steps and the counts; "効かせない" takes a group out of the ranking and the reasons; bad input is refused', async () => {
  const {env, sqlite} = await withIndex();
  const a = await signIn(env), b = await signIn(env);
  try {
    await rateSeen(env, a, '終わった舞台', '2026-08-05', '103', '◎');
    await rateSeen(env, a, '一日だけの舞台', '2026-09-05', '104', '×');
    let html = (await step(env, a, {get: '/api/screen/recommend'})).body.body_html;
    assert.match(html, /<details class="pbox wbox" id="weights">/);
    assert.match(html, /いまは<b>すべて「ふつう」（これまでと同じ効き方）<\/b>/);
    assert.match(html, /<div class="wrow" data-grp="cast"><span class="wl">出演者<\/span><span class="wn">おすすめの候補 1 件で一致<\/span>/);
    assert.match(html, /<h1>今週のおすすめ 1 件<\/h1>/);
    const saved = await step(env, a, {post: '/api/weight', body: {weights: {cast: 'off', theme: 'max'}}});
    assert.equal(saved.status, 200);
    assert.deepEqual(saved.body.weights, {cast: 'off', theme: 'max'});
    html = (await step(env, a, {get: '/api/screen/recommend'})).body.body_html;
    assert.match(html, /いまは<b>出演者を効かせない／作品の内容をとても強く<\/b>/);
    assert.match(html, /<div class="wrow off" data-grp="cast">/);
    assert.doesNotMatch(html, /<span class="net">人物<\/span>出演 /);   // the cast leaves the reasons too
    const all = Object.fromEntries(['cast', 'author', 'craft', 'stage', 'produce', 'other', 'theme'].map(k => [k, 'off']));
    assert.equal((await step(env, a, {post: '/api/weight', body: {weights: all}})).status, 200);
    assert.match((await step(env, a, {get: '/api/screen/recommend'})).body.body_html, /<h1>今週のおすすめはありません<\/h1>/);
    // Only the listed groups and steps; nothing is written when one is wrong.
    assert.equal((await step(env, a, {post: '/api/weight', body: {weights: {cast: 'mid', bogus: 'max'}}})).status, 400);
    assert.equal((await step(env, a, {post: '/api/weight', body: {weights: {cast: '9'}}})).status, 400);
    assert.equal(sqlite.prepare("SELECT step FROM rank_weight WHERE grp='cast'").get().step, 'off');
    // Back to ふつう brings it back; another user is never affected.
    await step(env, a, {post: '/api/weight', body: {weights: Object.fromEntries(Object.keys(all).map(k => [k, 'mid']))}});
    assert.match((await step(env, a, {get: '/api/screen/recommend'})).body.body_html, /<h1>今週のおすすめ 1 件<\/h1>/);
    assert.match((await step(env, b, {get: '/api/screen/recommend'})).body.body_html, /すべて「ふつう」/);
    // The rest of the screen's writes answer as the public Python service does.
    const visit = await step(env, a, {post: '/api/recommendation/visit', body: {stage_id: '101'}});
    assert.equal(visit.status, 200); assert.equal(visit.body.disabled, true);
    const theme = await step(env, a, {post: '/api/hand_theme', body: {stage_id: '101', words: 'x'}});
    assert.equal(theme.status, 400); assert.match(theme.body.error, /公開版では公演情報の編集はできません/);
  } finally { sqlite.close(); }
});
