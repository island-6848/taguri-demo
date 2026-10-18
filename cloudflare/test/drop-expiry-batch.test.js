// 30 日たった取り消しの記録を消すのは、画面を読むときに 1 回の batch・件数の上限つきで（issue #194）。
// 前は記録 1 件ごとに batch（4〜5 文）を流していたので、まとめて取り消した人が後で画面を開くと、
// その 1 回の表示で N 回の batch・4N 文の書き込みになった。消しきれなかった分は、消えるまで隠したまま次の表示で消す。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {setup, step, signIn} from './screens/harness.js';
import {loadWorks, EXPIRE_MAX} from '../src/screens/works.js';

const OLD = '2000-01-01 00:00:00';

/** env.DB の、消す文（DELETE）を含む batch の回数と、その文の数を数える（読み出しだけの batch は数えない） */
function counted(env) {
  const c = {batches: 0, statements: 0};
  const tagged = (st, sql) => ({...st, sql, bind: (...v) => tagged(st.bind(...v), sql)});
  return {c, env: {...env, DB: {...env.DB, prepare: sql => tagged(env.DB.prepare(sql), sql),
    batch(cs) { if (cs.some(x => /^\s*DELETE/i.test(x.sql))) { c.batches++; c.statements += cs.length; } return env.DB.batch(cs); }}}};
}

test('many expired drops go in one bounded batch per read, stay hidden meanwhile, and the other user is untouched', async () => {
  const {env, sqlite} = setup();
  const a = await signIn(env), b = await signIn(env);
  try {
    const keep = (await step(env, a, {post: '/api/add_work', body: {title: '残す記録', date: '2026-08-01'}})).body.work_key;
    const [ua, ub] = sqlite.prepare('SELECT id FROM users ORDER BY rowid').all().map(r => r.id);
    const n = EXPIRE_MAX + 10;
    const keys = Array.from({length: n}, (_, i) => `消す記録${i}#2026-07-01`);
    sqlite.exec('BEGIN');
    for (const u of [ua, ub]) for (const k of keys) {
      sqlite.prepare("INSERT INTO works(user_id,work_key,title,first_date,last_date,times,note_impression,note_motive,updated_at) VALUES(?,?,?,'2026-07-01','2026-07-01',1,'','',?)").run(u, k, k, OLD);
      sqlite.prepare("INSERT INTO hand_credits(user_id,work_key,fields,updated_at) VALUES(?,?,'{\"出演\":\"役者\"}',?)").run(u, k, OLD);
      // b の印は新しい（まだ 30 日たっていない）。a の印だけが期限切れ
      sqlite.prepare('INSERT INTO excluded(user_id,uid,program,updated_at) VALUES(?,?,?,?)').run(u, `work:${k}`, k, u === ua ? OLD : '2099-01-01 00:00:00');
    }
    sqlite.exec('COMMIT');
    const left = u => sqlite.prepare('SELECT count(*) n FROM works WHERE user_id=?').get(u).n;

    const {c, env: e} = counted(env);
    assert.equal((await step(e, a, {get: '/api/screen/unrated'})).status, 200);
    assert.ok(c.batches <= 1, `batches: ${c.batches}`);
    assert.ok(c.statements <= 10, `statements: ${c.statements}`);
    assert.equal(left(ua), 1 + n - EXPIRE_MAX);
    // 消しきれなかった分も、日記帳・設定の「取り消した記録」には出さない
    const ctx = {db: env.DB, uid: ua, today: env.CLOCK.today, now: env.CLOCK.now, dropExpired: true};
    assert.deepEqual((await loadWorks(ctx)).map(w => w.work_key), [keep]);
    const settings = (await step(env, a, {get: '/api/screen/settings'})).body.body_html;
    assert.doesNotMatch(settings, /消す記録/);

    await step(env, a, {get: '/api/screen/unrated'});
    assert.equal(left(ua), 1);
    assert.equal(sqlite.prepare('SELECT count(*) n FROM hand_credits WHERE user_id=?').get(ua).n, 0);
    assert.equal(sqlite.prepare('SELECT count(*) n FROM excluded WHERE user_id=?').get(ua).n, 0);
    assert.equal(left(ub), n);
    assert.equal(sqlite.prepare('SELECT count(*) n FROM hand_credits WHERE user_id=?').get(ub).n, n);
    assert.equal(sqlite.prepare('SELECT count(*) n FROM excluded WHERE user_id=?').get(ub).n, n);
  } finally { sqlite.close(); }
});

test('a record marked purged by an older version is hidden until it is deleted', async () => {
  const {env, sqlite} = setup();
  const a = await signIn(env);
  try {
    const k = (await step(env, a, {post: '/api/add_work', body: {title: '前の版で消した記録', date: '2026-08-01'}})).body.work_key;
    const uid = sqlite.prepare('SELECT id FROM users').get().id;
    sqlite.prepare('INSERT INTO excluded(user_id,uid,program,updated_at) VALUES(?,?,?,?)').run(uid, `purged:${k}`, k, OLD);
    assert.deepEqual(await loadWorks({db: env.DB, uid, today: env.CLOCK.today, now: env.CLOCK.now, dropExpired: true}), []);
    await step(env, a, {get: '/api/screen/unrated'});
    assert.equal(sqlite.prepare('SELECT count(*) n FROM works WHERE user_id=?').get(uid).n, 0);
  } finally { sqlite.close(); }
});
