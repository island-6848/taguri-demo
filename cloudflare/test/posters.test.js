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

test('R2 reads stop at the monthly cap (free tier) and fall through to Render', async () => {
  const {env, sqlite} = setup();
  const {r2ReadAllowed, r2Gate, R2_READS_CAP} = await import('../src/free-tier.js');
  const t = Date.parse('2026-10-20T00:00:00Z');
  try {
    Object.assign(r2Gate, {month: '', off: false, at: 0});
    // Every sampled read adds the sample size, so the total tracks the real reads.
    env.R2_READ_SAMPLE = '1';
    assert.equal(await r2ReadAllowed(env, t, () => 0), true);
    assert.equal(sqlite.prepare("SELECT n FROM usage WHERE k='r2_get:2026-10'").get().n, 1);
    sqlite.prepare("UPDATE usage SET n=? WHERE k='r2_get:2026-10'").run(R2_READS_CAP - 1);
    assert.equal(await r2ReadAllowed(env, t + 1000, () => 0), false);       // this read reaches the cap
    assert.equal(await r2ReadAllowed(env, t + 2000, () => 0.99), false);    // and the isolate remembers
    // Another isolate learns it from D1 within a minute, even without sampling.
    Object.assign(r2Gate, {month: '', off: false, at: 0});
    assert.equal(await r2ReadAllowed(env, t + 3000, () => 0.99), false);
    // A new month starts from zero.
    assert.equal(await r2ReadAllowed(env, Date.parse('2026-11-01T00:00:00Z'), () => 0.99), true);
    // Without the usage table (or any D1 error) R2 is not read at all.
    sqlite.exec('DROP TABLE usage');
    Object.assign(r2Gate, {month: '', off: false, at: 0});
    assert.equal(await r2ReadAllowed(env, t, () => 0.99), false);
  } finally { Object.assign(r2Gate, {month: '', off: false, at: 0}); sqlite.close(); }
});

test('/api/health reports the R2 read counter (counts only)', async () => {
  const {env, sqlite} = setup();
  try {
    const month = new Date().toISOString().slice(0, 7);
    sqlite.prepare('INSERT INTO usage(k, n) VALUES (?, 40)').run(`r2_get:${month}`);
    const h = await (await worker.fetch(new Request(`${ORIGIN}/api/health`), env)).json();
    assert.deepEqual(h.free_tier, {r2_reads_month: 40, r2_reads_cap: 3_000_000});
  } finally { sqlite.close(); }
});
