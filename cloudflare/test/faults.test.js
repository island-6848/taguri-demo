// 外部依存の停止・不正応答のときの保存と復帰（issue #141 の手順 1・2 のうち、手元の模擬で確かめられる分）。
// 本番のサービスは止めない。D1・R2・Firebase の失敗を作り物で起こし、保存の成否を誤って「保存しました」と言わないこと、
// 再試行で重複も消失もしないこと、利用者に日本語の案内を返すことを確かめる
import {test} from 'node:test';
import assert from 'node:assert/strict';
import worker from '../src/worker.js';
import {setup, signIn, step} from './screens/harness.js';

const ORIGIN = 'https://taguri.example';
const get = (env, cookie, path) => worker.fetch(new Request(ORIGIN + path, {headers: {cookie}}), env);

test('D1 が答えない: 画面の取得は 503 と日本語の案内（中身の SQL や例外は見せない）', async () => {
  const {env, sqlite} = setup();
  try {
    const a = await signIn(env);
    const down = {prepare: () => { throw new Error('D1_ERROR: database unavailable SELECT secret'); }, batch: async () => { throw new Error('D1_ERROR'); }};
    const res = await get({...env, DB: down}, a, '/api/screen/recommend');
    assert.equal(res.status, 503);
    const body = await res.json();
    assert.equal(body.ok, false);
    assert.match(body.error, /一時的にうまく動いていません/);
    assert.doesNotMatch(JSON.stringify(body), /D1_ERROR|SELECT|secret/);
    const page = await get({...env, DB: down}, a, '/recommend');
    assert.equal(page.status, 503);
    const html = await page.text();
    assert.match(html, /記録は消えていません/);
    assert.doesNotMatch(html, /D1_ERROR|SELECT/);
  } finally { sqlite.close(); }
});

test('評価の保存の途中で D1 が失敗: 「保存しました」と言わず、記録は変わらない。再試行で 1 件だけ保存される', async () => {
  const {env, sqlite} = setup();
  try {
    const a = await signIn(env);
    const k = (await step(env, a, {post: '/api/add_work', body: {title: '模擬の公演', date: '2026-09-01'}})).body.work_key;
    const before = sqlite.prepare('SELECT verdict FROM works WHERE work_key=?').get(k).verdict;
    const real = env.DB;
    const flaky = {prepare: sql => real.prepare(sql), batch: async () => { throw new Error('D1_ERROR: network connection lost'); }};
    const failRun = {prepare: sql => { const s = real.prepare(sql); if (/^\s*(INSERT|UPDATE|DELETE)/i.test(sql)) { const fail = () => Promise.reject(new Error('D1_ERROR: network connection lost')); const w = q => ({...q, bind: (...v) => w(q.bind(...v)), run: fail, all: fail, first: fail}); return w(s); } return s; }, batch: flaky.batch};
    const r1 = await step({...env, DB: failRun}, a, {post: '/api/rate', body: {work_key: k, verdict: '◎'}});
    assert.notEqual(r1.status, 200, '失敗したのに成功と返していない');
    assert.notEqual(r1.body?.ok, true);
    assert.equal(sqlite.prepare('SELECT verdict FROM works WHERE work_key=?').get(k).verdict, before);
    // 復帰後の再試行（同じ操作をもう 1 度）
    const r2 = await step(env, a, {post: '/api/rate', body: {work_key: k, verdict: '◎'}});
    assert.equal(r2.status, 200);
    const r3 = await step(env, a, {post: '/api/rate', body: {work_key: k, verdict: '◎'}});   // 応答が届かず、もう 1 度押した
    assert.equal(r3.status, 200);
    assert.equal(sqlite.prepare('SELECT count(*) n FROM works WHERE work_key=?').get(k).n, 1);
    assert.equal(sqlite.prepare('SELECT verdict FROM works WHERE work_key=?').get(k).verdict, '◎');
  } finally { sqlite.close(); }
});

test('記録の追加の応答が届かず、同じ内容でもう 1 度送った: 記録は 1 件のまま', async () => {
  const {env, sqlite} = setup();
  try {
    const a = await signIn(env);
    const body = {title: '二度押しの公演', date: '2026-09-02'};
    assert.equal((await step(env, a, {post: '/api/add_work', body})).status, 200);
    // 2 度目は「もう登録してある」と答える（失敗ではなく、すでに保存されていることを伝える）
    const again = await step(env, a, {post: '/api/add_work', body});
    assert.equal(again.status, 400);
    assert.match(again.body.error, /もう登録してある/);
    assert.equal(sqlite.prepare("SELECT count(*) n FROM works WHERE title='二度押しの公演'").get().n, 1);
  } finally { sqlite.close(); }
});

test('R2（ポスター）が失敗: その画像だけが失敗し、503 の短い答え。画面の取得は止まらない', async () => {
  const {env, sqlite} = setup();
  try {
    const a = await signIn(env);
    const posters = {get: async () => { throw new Error('R2 internal error'); }};
    const img = await get({...env, POSTERS: posters}, a, '/img/123.webp');
    assert.ok([404, 503].includes(img.status), String(img.status));
    assert.doesNotMatch(await img.text(), /R2 internal/);
    const screen = await get({...env, POSTERS: posters}, a, '/api/screen/recommend');
    assert.equal(screen.status, 200);
  } finally { sqlite.close(); }
});

test('Google のログインの鍵が取れない（Firebase の JWKS が 5xx・JSON でない）: ログインは失敗と答え、アカウントは作らない', async () => {
  const {env, sqlite} = setup();
  const realFetch = globalThis.fetch;
  try {
    const users = sqlite.prepare('SELECT count(*) n FROM users').get().n;
    for (const broken of [async () => new Response('<html>bad gateway</html>', {status: 502}), async () => { throw new Error('timeout'); }]) {
      globalThis.fetch = broken;
      const res = await worker.fetch(new Request(ORIGIN + '/api/auth/firebase', {method: 'POST', headers: {origin: ORIGIN, 'content-type': 'application/json'},
        body: JSON.stringify({idToken: 'eyJhbGciOiJSUzI1NiIsImtpZCI6IngifQ.eyJzdWIiOiJ4In0.c2ln'})}), {...env, FIREBASE_PROJECT_ID: 'taguri-test'});
      assert.ok(res.status >= 400, String(res.status));
      const j = await res.json().catch(() => null);
      assert.ok(j && j.ok !== true);
    }
    assert.equal(sqlite.prepare('SELECT count(*) n FROM users').get().n, users);
  } finally { globalThis.fetch = realFetch; sqlite.close(); }
});
