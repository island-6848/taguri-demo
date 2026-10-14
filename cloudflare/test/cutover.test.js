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
