// Posters from R2 (worker.js posterFromR2) and on the native screens (rate.posterHtml).
import {test} from 'node:test';
import assert from 'node:assert/strict';
import worker from '../src/worker.js';
import {posterHtml} from '../src/screens/rate.js';
import {setup, step, signIn} from './screens/harness.js';

const ORIGIN = 'https://taguri.example';
const bucket = files => ({async get(k) {
  if (!(k in files)) return null;
  return {body: new TextEncoder().encode(files[k]), httpMetadata: {contentType: 'image/jpeg'}, httpEtag: '"e1"'};
}});

test('/img/<file> comes from R2 for a signed-in user; a missing file falls through to Render', async () => {
  const {env, sqlite} = setup();
  env.POSTERS = bucket({'123.jpg': 'JPEG'});
  const cookie = await signIn(env);
  const real = globalThis.fetch, sent = [];
  globalThis.fetch = async url => { sent.push(new URL(String(url)).pathname); return new Response('from render'); };
  try {
    const hit = await worker.fetch(new Request(`${ORIGIN}/img/123.jpg`, {headers: {cookie}}), env);
    assert.equal(hit.status, 200);
    assert.equal(hit.headers.get('content-type'), 'image/jpeg');
    assert.equal(await hit.text(), 'JPEG');
    const miss = await worker.fetch(new Request(`${ORIGIN}/img/999.jpg`, {headers: {cookie}}), env);
    assert.equal(await miss.text(), 'from render');
    assert.deepEqual(sent, ['/img/999.jpg']);
    const anon = await worker.fetch(new Request(`${ORIGIN}/img/123.jpg`), env);
    assert.equal(anon.status, 401);                        // posters are for signed-in users only
  } finally { globalThis.fetch = real; sqlite.close(); }
});

test("posterHtml draws the linked stage's poster only when it is listed", () => {
  assert.equal(posterHtml({stage_id: '5'}, {}), '');
  assert.equal(posterHtml({stage_id: ''}, {'': 'x.jpg'}), '');
  assert.match(posterHtml({stage_id: '5'}, {'5': '5.jpg'}), /<img class="poster" src="\/img\/5\.jpg\?t=__TAGURI_TOKEN__"/);
});

test('the native 日記帳 shows the poster of a record linked to a stage in R2', async () => {
  const {env, sqlite} = setup();
  env.NATIVE_UI = 'all';
  const cookie = await signIn(env);
  try {
    const key = (await step(env, cookie, {post: '/api/add_work', body: {title: '夜の果て', date: '2026-08-01'}})).body.work_key;
    sqlite.prepare("UPDATE works SET stage_id='777' WHERE work_key=?").run(key);
    sqlite.prepare("INSERT INTO poster(stage_id, file) VALUES ('777', '777.jpg')").run();
    const html = (await step(env, cookie, {get: '/api/screen/works'})).body.body_html;
    assert.match(html, /src="\/img\/777\.jpg\?t=__TAGURI_TOKEN__"/);
  } finally { sqlite.close(); }
});
