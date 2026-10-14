// Switching screens from Render to the Worker (NATIVE_UI), before it is done in
// production (docs/knowledge: q-native-cutover). Covers what screens.test.js
// does not: a partial list, the unset default, and two users through the
// native screens.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import worker from '../src/worker.js';
import {setup, step, signIn} from './screens/harness.js';

const ORIGIN = 'https://taguri.example';
/** Records what the bridge would send to Render instead of sending it. */
function stubRender() {
  const sent = [];
  const real = globalThis.fetch;
  globalThis.fetch = async (url, init = {}) => {
    sent.push(`${init.method || 'GET'} ${new URL(String(url)).pathname}`);
    return new Response(JSON.stringify({ok: true, from: 'render'}), {headers: {'content-type': 'application/json'}});
  };
  return {sent, restore: () => { globalThis.fetch = real; }};
}

test('a partial NATIVE_UI list answers only the listed names; the rest still go to Render', async () => {
  const {env, sqlite} = setup();
  env.NATIVE_UI = 'screen:works, api:add_work';
  const cookie = await signIn(env);
  const r = stubRender();
  try {
    const works = await step(env, cookie, {get: '/api/screen/works'});
    assert.equal(works.status, 200);
    assert.equal(works.body.edition, 'service');                 // answered by the Worker
    const add = await step(env, cookie, {post: '/api/add_work', body: {title: '夜の果て', date: '2026-08-01'}});
    assert.equal(add.status, 200);
    assert.match((await step(env, cookie, {get: '/api/screen/works'})).body.body_html, /夜の果て/);
    for (const s of [{get: '/api/screen/rate'}, {get: '/api/screen/recommend'}, {post: '/api/rate', body: {work_key: add.body.work_key, verdict: '◎'}}]) {
      const got = await step(env, cookie, s);
      assert.equal(got.body.from, 'render', JSON.stringify(s));
    }
    assert.deepEqual(r.sent, ['GET /api/screen/rate', 'GET /api/screen/recommend', 'POST /api/rate']);
  } finally { r.restore(); sqlite.close(); }
});

test('with NATIVE_UI unset every screen and write goes to Render (production today)', async () => {
  const {env, sqlite} = setup();
  delete env.NATIVE_UI;
  const cookie = await signIn(env);
  const r = stubRender();
  try {
    for (const s of [{get: '/api/screen/works'}, {get: '/api/screen/rate'}, {post: '/api/add_work', body: {title: 'x', date: '2026-08-01'}}]) {
      assert.equal((await step(env, cookie, s)).body.from, 'render', JSON.stringify(s));
    }
    assert.equal(sqlite.prepare('SELECT count(*) AS n FROM works').get().n, 0);
  } finally { r.restore(); sqlite.close(); }
});

test("two users on the native screens never see or change each other's records", async () => {
  const {env, sqlite} = setup();
  const a = await signIn(env), b = await signIn(env);
  try {
    const key = (await step(env, a, {post: '/api/add_work', body: {title: 'Aだけの舞台', date: '2026-08-01'}})).body.work_key;
    assert.equal((await step(env, a, {post: '/api/rate', body: {work_key: key, verdict: '◎'}})).status, 200);
    assert.equal((await step(env, a, {post: '/api/note', body: {work_key: key, note_impression: 'Aの感想'}})).status, 200);
    for (const path of ['/api/screen/works', '/api/screen/rate', '/api/screen/notes', '/api/screen/unrated']) {
      const html = (await step(env, b, {get: path})).body.body_html;
      assert.doesNotMatch(html, /Aだけの舞台|Aの感想/, path);
    }
    // B cannot write to A's record by naming its key.
    for (const s of [{post: '/api/rate', body: {work_key: key, verdict: '×'}},
      {post: '/api/note', body: {work_key: key, note_impression: 'B'}},
      {post: '/api/drop_work', body: {work_key: key}},
      {post: '/api/link_stage', body: {work_key: key, stage_id: ''}}]) {
      assert.equal((await step(env, b, s)).status, 400, JSON.stringify(s));
    }
    const row = sqlite.prepare('SELECT verdict, note_impression, stage_off FROM works WHERE work_key=?').get(key);
    assert.deepEqual({...row}, {verdict: '◎', note_impression: 'Aの感想', stage_off: 0});
    assert.match((await step(env, a, {get: '/api/screen/works'})).body.body_html, /Aだけの舞台/);
  } finally { sqlite.close(); }
});

// 2026-10-14: production switched before every screen was ported (起案者の指示
// 「本番用のサイトなはずなのに、デモ用の内容がでる。最初ログインしたらデータは空なはず」).
test('NATIVE_UI=all: nothing of a user goes to Render; unported screens and writes say they are moving', async () => {
  const {env, sqlite} = setup();
  const cookie = await signIn(env);
  const r = stubRender();
  try {
    for (const name of ['records', 'trace', 'chronicle']) {
      const got = await step(env, cookie, {get: `/api/screen/${name}`});
      assert.equal(got.status, 200, name);
      assert.equal(got.body.moving, true, name);
      assert.equal(got.body.edition, 'service', name);
      assert.match(got.body.body_html, /いま新しい仕組みに移しています/, name);
    }
    for (const path of ['/api/weight', '/api/recommendation/visit', '/api/hand_theme']) {
      const got = await step(env, cookie, {post: path, body: {}});
      assert.equal(got.status, 503, path);
      assert.match(got.body.error, /移している/, path);
    }
    // Stage suggestions are answered from D1, never with the demo's records.
    const sug = await step(env, cookie, {get: '/api/suggest?q=' + encodeURIComponent('舞台')});
    assert.equal(sug.status, 200);
    assert.ok(Array.isArray(sug.body.rows));
    // A new account starts empty.
    for (const path of ['/api/screen/works', '/api/screen/rate', '/api/screen/unrated', '/api/screen/notes']) {
      assert.equal((await step(env, cookie, {get: path})).status, 200, path);
    }
    assert.equal(sqlite.prepare('SELECT count(*) AS n FROM works').get().n, 0);
    // おすすめ is answered by the Worker too (recommend-screen.test.js), empty for a new account.
    assert.match((await step(env, cookie, {get: '/api/screen/recommend'})).body.body_html, /今週のおすすめはありません/);
    // Only posters missing from R2 may still be fetched from Render.
    await step(env, cookie, {get: '/img/101.jpg'});
    assert.deepEqual(r.sent, ['GET /img/101.jpg']);
  } finally { r.restore(); sqlite.close(); }
});

test('signed out, a moving screen still asks to sign in', async () => {
  const {env, sqlite} = setup();
  try {
    assert.equal((await step(env, 'x=y', {get: '/api/screen/records'})).status, 401);
  } finally { sqlite.close(); }
});

test('the account page shows only the signed-in user, and saves a display name', async () => {
  const {env, sqlite} = setup();
  const a = await signIn(env), b = await signIn(env);
  try {
    const empty = await step(env, a, {get: '/api/screen/account'});
    assert.equal(empty.status, 200);
    assert.equal(empty.body.title, 'アカウント');
    assert.match(empty.body.body_html, /あなただけが見られるページ/);
    assert.match(empty.body.body_html, /<b>0<\/b><span>観た作品/);
    const key = (await step(env, a, {post: '/api/add_work', body: {title: 'Aの舞台', date: '2026-08-01'}})).body.work_key;
    await step(env, a, {post: '/api/rate', body: {work_key: key, verdict: '◎'}});
    await step(env, a, {post: '/api/note', body: {work_key: key, note_impression: 'よかった'}});
    const saved = await step(env, a, {post: '/api/account', body: {display_name: ' 観劇好き '}});
    assert.equal(saved.status, 200);
    assert.equal(saved.body.display_name, '観劇好き');
    const page = (await step(env, a, {get: '/api/screen/account'})).body.body_html;
    assert.match(page, /観劇好き/);
    assert.match(page, /<b>1<\/b><span>観た作品/);
    assert.match(page, /<b>1<\/b><span>評価した作品/);
    assert.match(page, /<b>1<\/b><span>感想/);
    assert.match(page, /復旧コード/);
    // B sees none of A.
    const other = (await step(env, b, {get: '/api/screen/account'})).body.body_html;
    assert.doesNotMatch(other, /観劇好き/);
    assert.match(other, /<b>0<\/b><span>観た作品/);
    // Too long, or not text, is refused; an empty name clears it.
    assert.equal((await step(env, a, {post: '/api/account', body: {display_name: 'あ'.repeat(31)}})).status, 400);
    assert.equal((await step(env, a, {post: '/api/account', body: {display_name: 3}})).status, 400);
    assert.equal((await step(env, a, {post: '/api/account', body: {display_name: '<b>x</b>'}})).status, 200);
    assert.match((await step(env, a, {get: '/api/screen/account'})).body.body_html, /&lt;b&gt;x&lt;\/b&gt;/);
    assert.equal((await step(env, a, {post: '/api/account', body: {display_name: ''}})).status, 200);
    assert.equal(sqlite.prepare("SELECT count(*) AS n FROM app_setting WHERE key='display_name'").get().n, 0);
  } finally { sqlite.close(); }
});

test('stage suggestions come from the user\'s own records and the past stages in D1', async () => {
  const {env, sqlite} = setup();
  const a = await signIn(env), b = await signIn(env);
  try {
    sqlite.prepare("INSERT INTO past_stage(stage_id,title,tkey,start,end,venue,grp,pref,people) VALUES('9001','夜の果てまで','夜の果てまで','2024-05-01','2024-05-06','劇場Z','劇団Q','東京都','[]')").run();
    await step(env, a, {post: '/api/add_work', body: {title: '夜の果て', date: '2026-08-01'}});
    const got = (await step(env, a, {get: '/api/suggest?q=' + encodeURIComponent('夜の果て')})).body.rows;
    assert.deepEqual(got.map(r => [r.kind, r.title]), [['record', '夜の果て'], ['stage', '夜の果てまで']]);
    assert.equal(got[1].note, '劇団Q／2024/5/1〜2024/5/6（東京都）');
    // Another user never gets A's record.
    const other = (await step(env, b, {get: '/api/suggest?q=' + encodeURIComponent('夜の果て')})).body.rows;
    assert.deepEqual(other.map(r => r.kind), ['stage']);
  } finally { sqlite.close(); }
});
