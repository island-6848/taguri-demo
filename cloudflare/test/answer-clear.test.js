import {test} from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {reactAction} from '../src/screens/recommend.js';
import {reactionsOf} from '../src/screens/lists.js';

function setup() {
  const sql = new DatabaseSync(':memory:');
  sql.exec(`CREATE TABLE reaction(user_id TEXT,label TEXT,stage_id TEXT,interest INTEGER,owned INTEGER,note TEXT,note_no TEXT,note_pre TEXT,
    why TEXT,source TEXT,updated_at TEXT,rank INTEGER,score REAL,ver TEXT,arm TEXT,PRIMARY KEY(user_id,label,stage_id));
    CREATE TABLE rec_cache(user_id TEXT PRIMARY KEY,body TEXT);
    CREATE TABLE app_setting(user_id TEXT,key TEXT,value TEXT);
    CREATE TABLE ticket(user_id TEXT,stage_id TEXT,date TEXT);
    INSERT INTO ticket VALUES('alice','101','2026-11-01');`);
  const wrap = (s, a = []) => ({bind(...args) { return wrap(s, args); },
    async first() { return sql.prepare(s).get(...a) || null; }, async all() { return {results: sql.prepare(s).all(...a)}; },
    async run() { return sql.prepare(s).run(...a); }});
  const ctx = {uid: 'alice', today: '2026-10-19', now: Date.parse('2026-10-19T04:00:00Z'),
    db: {prepare: wrap, async batch(stmts) { sql.exec('BEGIN'); try { const r = []; for (const st of stmts) r.push(await st.run()); sql.exec('COMMIT'); return r; }
      catch (e) { sql.exec('ROLLBACK'); throw e; } }}};
  return {sql, ctx};
}

test('explicit clear removes every historical answer for this user and the tour, retaining notes and tickets', async () => {
  const {sql, ctx} = setup();
  try {
    for (const uid of ['alice', 'bob']) for (const day of ['2026-10-17', '2026-10-18']) for (const sid of ['101', '102']) {
      sql.prepare('INSERT INTO reaction(user_id,label,stage_id,interest,owned,note,updated_at) VALUES(?,?,?,?,?,?,?)')
        .run(uid, day, sid, 1, 1, '残すメモ', day + 'T00:00:00Z');
    }
    sql.exec(`INSERT INTO rec_cache VALUES('alice','{}'),('bob','{}')`);
    const result = await reactAction({stage_id: '101', clear: true, siblings: ['102', 'bad/id', '102']}, ctx);
    assert.equal(result.body.cleared, true);
    const a = await reactionsOf(ctx);
    for (const sid of ['101', '102']) { assert.equal(a.get(sid).interest, undefined); assert.equal(a.get(sid).owned, undefined); assert.equal(a.get(sid).note, '残すメモ'); }
    assert.equal(sql.prepare('SELECT count(*) AS n FROM reaction WHERE user_id=? AND interest=1').get('bob').n, 4);
    assert.equal(sql.prepare("SELECT count(*) AS n FROM ticket").get().n, 1);
    assert.equal(sql.prepare("SELECT count(*) AS n FROM rec_cache WHERE user_id='alice'").get().n, 0);
    assert.equal(sql.prepare("SELECT count(*) AS n FROM rec_cache WHERE user_id='bob'").get().n, 1);
    await reactAction({stage_id: '101', clear: true, siblings: ['102']}, ctx); // retry is idempotent
    await reactAction({stage_id: '101', value: 'interest', nofill: true, siblings: ['102']}, ctx);
    assert.equal((await reactionsOf(ctx)).get('102').interest, 1);
  } finally { sql.close(); }
});

test('all answer options can be explicitly cleared, and a repeated set remains idempotent', async () => {
  const {sql, ctx} = setup();
  try {
    for (const value of ['interest', 'nointerest', 'cantgo', 'owned']) {
      await reactAction({stage_id: '101', value, nofill: true}, ctx);
      await reactAction({stage_id: '101', value, nofill: true}, ctx);
      assert.ok(sql.prepare('SELECT * FROM reaction WHERE user_id=?').get('alice'));
      await reactAction({stage_id: '101', clear: true}, ctx);
      const r = (await reactionsOf(ctx)).get('101');
      assert.equal(r.interest, undefined); assert.equal(r.owned, undefined);
    }
    await assert.rejects(reactAction({stage_id: 'bad/id', clear: true}, ctx));
    await assert.rejects(reactAction({stage_id: '101', value: 'interest', clear: true}, ctx));
  } finally { sql.close(); }
});

test('a failed sibling reset rolls back the entire clear', async () => {
  const {sql, ctx} = setup();
  try {
    await reactAction({stage_id: '101', value: 'interest', siblings: ['102'], nofill: true}, ctx);
    sql.exec("CREATE TRIGGER fail_clear BEFORE UPDATE ON reaction WHEN OLD.stage_id='102' BEGIN SELECT RAISE(ABORT,'blocked'); END;");
    await assert.rejects(reactAction({stage_id: '101', clear: true, siblings: ['102']}, ctx));
    assert.equal((await reactionsOf(ctx)).get('101').interest, 1);
  } finally { sql.close(); }
});
