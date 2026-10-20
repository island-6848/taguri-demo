import {test} from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {suggest} from '../src/screens/suggest.js';
import {rateScreens} from '../src/screens/rate.js';

function fixture() {
  const db = new DatabaseSync(':memory:');
  db.exec(`CREATE TABLE works(user_id TEXT,work_key TEXT,title TEXT,first_date TEXT,last_date TEXT,times INTEGER,verdict TEXT,chosen TEXT,
    note_impression TEXT,note_motive TEXT,stage_id TEXT,venue TEXT,time TEXT,updated_at TEXT,PRIMARY KEY(user_id,work_key));
    CREATE TABLE excluded(user_id TEXT,uid TEXT,updated_at TEXT);
    CREATE TABLE merges(user_id TEXT,work_key TEXT,into_key TEXT);
    CREATE TABLE hand_credits(user_id TEXT,work_key TEXT,fields TEXT,poster TEXT);
    CREATE TABLE rec_meta(k TEXT,v TEXT);
    CREATE TABLE past_stage(stage_id TEXT,title TEXT,tkey TEXT,start TEXT,end TEXT,venue TEXT,grp TEXT,pref TEXT);
    CREATE INDEX past_title ON past_stage(tkey);
    CREATE TABLE poster(stage_id TEXT,file TEXT);`);
  const statement = (sql, args = []) => ({bind(...values) {return statement(sql, values)},
    async first() {return db.prepare(sql).get(...args)},
    async all() {return {results: db.prepare(sql).all(...args)}},
    async run() {return db.prepare(sql).run(...args)}});
  const ctx = {db: {prepare: sql => statement(sql), batch: cs => Promise.all(cs.map(c => c.all()))}, uid: 'one', now: Date.parse('2026-10-19T03:00:00Z'), today: '2026-10-19'};
  const stage = (id, venue = '東京劇場', group = '劇団甲', start = '2026-01-01', end = '2026-01-31') =>
    db.prepare('INSERT INTO past_stage VALUES(?,?,?,?,?,?,?,?)').run(String(id), '演劇の夜', '演劇の夜', start, end, venue, group, '東京都');
  return {db, ctx, stage};
}

test('detail search filters venue, group and attendance date before the past-candidate limit', async () => {
  const {db, ctx, stage} = fixture();
  try {
    for (let i = 1; i <= 25; i++) stage(i, '別の劇場');
    stage(99); stage(100, '東京劇場', '別の団体'); stage(101, '東京劇場', '劇団甲', '2025-01-01', '2025-01-31');
    const result = await suggest(new URLSearchParams({q: '演劇', advanced: '1', venue: '東京', group: '劇団甲', date: '2026-01-02'}), ctx);
    assert.deepEqual(result.rows.map(r => r.stage_id), ['99']);
    assert.equal(result.rows[0].venue, '東京劇場');
    assert.deepEqual((await suggest(new URLSearchParams({q: '演劇', advanced: '1', venue: "' OR 1=1 --"}), ctx)).rows, []);
    assert.match((await suggest(new URLSearchParams({q: '演劇', advanced: '1', date: '2026-02-30'}), ctx)).error, /正しく/);
  } finally {db.close()}
});

test('repeated attendance saves distinct days and matinee/evening; duplicate stays rejected', async () => {
  const {db, ctx, stage} = fixture(); stage(99);
  const add = (date, time, repeat = true) => rateScreens.actions.add_work({title: '演劇の夜', stage_id: '99', venue: '東京劇場', date, time, repeat}, ctx);
  try {
    for (const [date, time] of [['2026-01-02', '14:00'], ['2026-01-02', '19:00'], ['2026-01-03', '14:00']]) {
      assert.deepEqual((await add(date, time)).body.similar, []);
    }
    assert.equal(db.prepare('SELECT count(*) AS n FROM works WHERE user_id=?').get('one').n, 3);
    await assert.rejects(add('2026-01-02', '19:00'), /もうある/);
    assert.equal(db.prepare('SELECT count(*) AS n FROM works').get().n, 3);
    assert.ok((await add('2026-01-04', '14:00', false)).body.similar.length);
    const suggestions = await suggest(new URLSearchParams({q: '演劇', advanced: '1'}), ctx);
    assert.ok(suggestions.rows.every(r => r.kind === 'stage'));
    assert.ok(suggestions.rows[0].mine >= 3);
  } finally {db.close()}
});

test('schedule precision filters runs, including recurring months after the first twenty candidates', async () => {
  const {db, ctx, stage} = fixture();
  try {
    for (let i = 1; i <= 25; i++) stage(i, '東京劇場', '劇団甲', '2025-12-01', '2025-12-15');
    stage(99, '東京劇場', '劇団甲', '2026-01-20', '2026-03-05');
    stage(100, '東京劇場', '劇団甲', '2024-02-29', '2024-02-29');
    const ids = async parts => (await suggest(new URLSearchParams({q: '演劇', advanced: '1', ...parts}), ctx)).rows.map(r => r.stage_id);
    assert.deepEqual(await ids({schedule_precision: 'month', schedule_month: '2'}), ['99', '100']);
    assert.deepEqual(await ids({schedule_precision: 'monthday', schedule_month: '2', schedule_day: '29'}), ['100']);
    assert.deepEqual(await ids({schedule_precision: 'yearmonth', schedule_year: '2026', schedule_month: '2'}), ['99']);
    assert.deepEqual(await ids({schedule_precision: 'date', schedule_year: '2026', schedule_month: '3', schedule_day: '5'}), ['99']);
    assert.deepEqual(await ids({schedule_precision: 'date', schedule_year: '2026', schedule_month: '3', schedule_day: '6'}), []);
    assert.deepEqual(await ids({schedule_day: '31'}), ['99']);
    assert.deepEqual(await ids({schedule_year: '2024', schedule_day: '29'}), ['100']);
    assert.deepEqual(await ids({schedule_year: '2026', schedule_month: '2'}), ['99']);
  } finally {db.close()}
});

test('schedule filtering also reaches current catalogue candidates beyond the default twenty', async () => {
  const {db, ctx} = fixture();
  try {
    db.exec(`CREATE TABLE rec_gram(ver TEXT,gram TEXT,part INTEGER,entries TEXT);
      CREATE TABLE rec_stage(ver TEXT,stage_id TEXT,title TEXT,tkey TEXT,grp TEXT,start TEXT,end TEXT,entry TEXT);
      INSERT INTO rec_meta VALUES('current','v');`);
    const entries = [];
    for (let i = 1; i <= 30; i++) {
      const sid = String(i).padStart(2, '0'), month = i === 30 ? '02' : '12';
      const start = `2026-${month}-01`, end = `2026-${month}-20`;
      entries.push([sid, '演劇の夜', start, end]);
      db.prepare('INSERT INTO rec_stage VALUES(?,?,?,?,?,?,?,?)').run('v', sid, '演劇の夜', '演劇の夜', '劇団甲', start, end, JSON.stringify({theater: '東京劇場'}));
    }
    db.prepare('INSERT INTO rec_gram VALUES(?,?,?,?)').run('v', '演劇', 0, JSON.stringify(entries));
    const result = await suggest(new URLSearchParams({q: '演劇', advanced: '1', schedule_precision: 'month', schedule_month: '2'}), ctx);
    assert.deepEqual(result.rows.map(r => r.stage_id), ['30']);
  } finally {db.close()}
});
