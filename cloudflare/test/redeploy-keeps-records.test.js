// 再配備（新しい Worker のコード・推薦の VERSION の更新）と索引の入れ替えで変わるのは、おすすめの作り置き
// （rec_cache）などの控えだけで、本人の記録は 1 つも変わらないこと（issue #137）。
// - Worker のコードは DB の形を変えない（src に CREATE・ALTER・DROP が無い。形を変えるのは migrations/ だけ）
// - 起動のときに走る書き込みは無い。要求の無いときに動くのは定期実行（cleanup.test.js で確かめる）だけ
// - 前の版の作り置きは、印（stamp）の先頭の VERSION が違うので読まれず、次に開いたときに上書きされる
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {readFileSync, readdirSync} from 'node:fs';
import {setup, step, signIn} from './screens/harness.js';
import worker from '../src/worker.js';

const here = p => new URL(p, import.meta.url).pathname;
const FIXTURE = JSON.parse(execFileSync('python3', [here('./screens/recommend_fixture.py')], {encoding: 'utf8', maxBuffer: 64 * 1024 * 1024}));
const VERSION = readFileSync(here('../src/screens/recommend.js'), 'utf8').match(/const VERSION = '([^']+)'/)[1];
// 本人の記録ではない表（作り置き・測るための控え・ログインの途中）
const CACHES = new Set(['rec_cache', 'rec_shown', 'webauthn_challenges']);

function srcFiles(dir) {
  return readdirSync(dir, {withFileTypes: true}).flatMap(e => e.isDirectory() ? srcFiles(`${dir}/${e.name}`) : /\.js$/.test(e.name) ? [`${dir}/${e.name}`] : []);
}
const userTables = sqlite => sqlite.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").all().map(r => r.name)
  .filter(t => t === 'users' || sqlite.prepare(`PRAGMA table_info(${t})`).all().some(c => c.name === 'user_id'));
const records = sqlite => Object.fromEntries(userTables(sqlite).filter(t => !CACHES.has(t)).sort()
  .map(t => [t, sqlite.prepare(`SELECT * FROM ${t} ORDER BY 1, 2`).all().map(r => ({...r}))]));

test('the Worker code never changes the shape of the database', () => {
  for (const f of srcFiles(here('../src'))) {
    const text = readFileSync(f, 'utf8');
    assert.doesNotMatch(text, /\b(CREATE|ALTER|DROP)\s+(TABLE|INDEX|TRIGGER|VIEW)\b/i, f);
  }
});

async function rateSeen(env, cookie, title, date, sid, verdict) {
  const key = (await step(env, cookie, {post: '/api/add_work', body: {title, date}})).body.work_key;
  assert.equal((await step(env, cookie, {post: '/api/link_stage', body: {work_key: key, stage_id: sid}})).status, 200);
  assert.equal((await step(env, cookie, {post: '/api/rate', body: {work_key: key, verdict}})).status, 200);
}

test('after a redeploy (new VERSION) and a new index, the records are the same and only the cache is rebuilt', async () => {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  const a = await signIn(env), b = await signIn(env);
  try {
    await rateSeen(env, a, '終わった舞台', '2026-08-05', '103', '◎');
    await rateSeen(env, a, '一日だけの舞台', '2026-09-05', '104', '×');
    await rateSeen(env, b, '終わった舞台', '2026-08-06', '103', '○');
    const uidA = sqlite.prepare('SELECT user_id FROM works ORDER BY rowid LIMIT 1').get().user_id;
    // 画面の外で足される本人の入力（設定・お気に入り）
    sqlite.prepare("INSERT INTO app_setting(user_id,key,value,updated_at) VALUES(?,'rating_scale','star','2026-10-01 00:00:00')").run(uidA);
    sqlite.prepare("INSERT INTO favourites(user_id,name,kind) VALUES(?,'どこにも出ない人','人')").run(uidA);
    const first = (await step(env, a, {get: '/api/screen/recommend'})).body.body_html;
    assert.match(first, /<article class="ticket recommend" data-stage="101"/);
    const cached = sqlite.prepare('SELECT stamp FROM rec_cache WHERE user_id=?').get(uidA).stamp;
    assert.ok(cached.startsWith(VERSION + '|'));
    const before = records(sqlite);

    // 再配備: 前の版のコードが書いた作り置き（印の先頭が古い VERSION）が残っている
    sqlite.prepare('UPDATE rec_cache SET stamp=?, body=? WHERE user_id=?').run(cached.replace(VERSION, 'screen-v0'), '{"old":true}', uidA);
    for (const path of ['recommend', 'interest', 'favourites', 'works', 'rate', 'records', 'settings', 'account', 'reminder'])
      assert.equal((await step(env, a, {get: `/api/screen/${path}`})).status, 200, path);   // 古いブラウザーの Cookie のまま
    const again = sqlite.prepare('SELECT stamp, body FROM rec_cache WHERE user_id=?').get(uidA);
    assert.ok(again.stamp.startsWith(VERSION + '|'), '作り置きは今の版で作り直す');
    assert.notEqual(again.body, '{"old":true}');
    assert.equal((await step(env, a, {get: '/api/screen/recommend'})).body.body_html, first);

    // 索引の入れ替え（取得の差分配送で index_rev が進む）: 作り置きは作り直し、記録はそのまま
    sqlite.prepare("INSERT INTO rec_meta(k,v) VALUES('index_rev','next') ON CONFLICT(k) DO UPDATE SET v=excluded.v").run();
    assert.equal((await step(env, a, {get: '/api/screen/recommend'})).status, 200);
    assert.match(sqlite.prepare('SELECT stamp FROM rec_cache WHERE user_id=?').get(uidA).stamp, /\|next\|/);

    // 定期実行（再配備のあとも同じ）は、記録のあるアカウントに触らない
    const waits = [];
    await worker.scheduled({}, env, {waitUntil: p => waits.push(p)});
    await Promise.all(waits);
    assert.deepEqual(records(sqlite), before);
  } finally { sqlite.close(); }
});
