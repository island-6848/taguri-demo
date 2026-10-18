// その日に出した公演（rec_shown）を 2 つの画面から同時に足しても、どちらの公演も残り、1 日の書き直しの上限
// （SHOWN_WRITES_MAX）と分析から外れる設定も守る（issue #190）。前は読んでから JS で足して書いていたので、
// 同じ元の並びを読んだ 2 つの書き込みの後の方が、先の方の公演を消していた。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {setup, signIn} from './screens/harness.js';
import {recordShown, SHOWN_WRITES_MAX, OPTOUT_KEY} from '../src/screens/evalrec.js';

/** recordShown の読み出し（rec_shown を引く SELECT）を、n 回そろうまで止める。そろったら then を 1 回だけ流す */
function barrier(env, n, then = () => {}) {
  const db = env.DB;
  let waiting = 0, open, done = false;
  const gate = new Promise(r => { open = r; });
  const prepare = sql => {
    const s = db.prepare(sql);
    if (!/LEFT JOIN rec_shown/.test(sql)) return s;
    const hold = st => ({...st, bind: (...v) => hold(st.bind(...v)), async first() {
      const row = await st.first();
      if (!done) { if (++waiting === n) { done = true; then(); open(); } await gate; }
      return row;
    }});
    return hold(s);
  };
  return {...db, prepare};
}

async function start() {
  const {env, sqlite} = setup();
  await signIn(env);
  const uid = sqlite.prepare('SELECT id FROM users').get().id;
  const ctx = db => ({db, uid, today: env.CLOCK.today, now: env.CLOCK.now});
  const row = () => { const r = sqlite.prepare('SELECT ids, writes FROM rec_shown WHERE user_id=?').get(uid); return r && {ids: JSON.parse(r.ids).sort(), writes: r.writes}; };
  return {env, sqlite, uid, ctx, row};
}

test('two screens adding at once both keep their stages', async () => {
  const {env, sqlite, ctx, row} = await start();
  try {
    assert.equal(await recordShown(ctx(env.DB), 'recommend', ['a']), true);
    const db = barrier(env, 2);
    await Promise.all([recordShown(ctx(db), 'recommend', ['b']), recordShown(ctx(db), 'recommend', ['c'])]);
    assert.deepEqual(row(), {ids: ['a', 'b', 'c'], writes: 3});
  } finally { sqlite.close(); }
});

test('the first row of the day written from two screens at once keeps both', async () => {
  const {env, sqlite, ctx, row} = await start();
  try {
    const db = barrier(env, 2);
    await Promise.all([recordShown(ctx(db), 'recommend', ['b']), recordShown(ctx(db), 'recommend', ['c'])]);
    assert.deepEqual(row(), {ids: ['b', 'c'], writes: 2});
  } finally { sqlite.close(); }
});

test('the daily write cap holds when two writes race for the last one', async () => {
  const {env, sqlite, ctx, row} = await start();
  try {
    for (let i = 0; i < SHOWN_WRITES_MAX - 1; i++) assert.equal(await recordShown(ctx(env.DB), 'recommend', [`s${i}`]), true);
    assert.equal(row().writes, SHOWN_WRITES_MAX - 1);
    const db = barrier(env, 2);
    const done = await Promise.all([recordShown(ctx(db), 'recommend', ['x']), recordShown(ctx(db), 'recommend', ['y'])]);
    assert.deepEqual(done.sort(), [false, true]);
    assert.equal(row().writes, SHOWN_WRITES_MAX);
  } finally { sqlite.close(); }
});

test('opting out between the read and the write stops the write', async () => {
  for (const first of [true, false]) {
    const {env, sqlite, uid, ctx, row} = await start();
    try {
      if (!first) await recordShown(ctx(env.DB), 'recommend', ['a']);
      const before = row();
      const db = barrier(env, 1, () => sqlite.prepare("INSERT INTO app_setting(user_id,key,value,updated_at) VALUES(?,?,'1','x')").run(uid, OPTOUT_KEY));
      assert.equal(await recordShown(ctx(db), 'recommend', ['b']), false);
      assert.deepEqual(row(), before);
    } finally { sqlite.close(); }
  }
});
