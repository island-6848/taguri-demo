// Automatic linking of a user's records to the stage they saw (screens/autolink.js).
import {DatabaseSync} from 'node:sqlite';
import {readFileSync, readdirSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {autoLink, pickStage} from '../src/screens/autolink.js';
import {titleKey} from '../src/screens/works.js';

function setup() {
  const sqlite = new DatabaseSync(':memory:');
  for (const f of readdirSync(new URL('../migrations/', import.meta.url)).filter(n => n.endsWith('.sql')).sort()) sqlite.exec(readFileSync(new URL(`../migrations/${f}`, import.meta.url), 'utf8'));
  sqlite.exec('PRAGMA foreign_keys = OFF');
  const wrap = (sql, args = []) => ({bind(...v) { return wrap(sql, v); }, async first() { return sqlite.prepare(sql).get(...args) ?? null; }, async all() { return {results: sqlite.prepare(sql).all(...args)}; }, async run() { return sqlite.prepare(sql).run(...args); }, async execute() { return /^\s*SELECT/.test(sql) ? this.all() : this.run(); }});
  const db = {prepare: sql => wrap(sql), async batch(cs) { const r = []; for (const c of cs) r.push(await c.execute()); return r; }};
  const work = (uid, title, date, extra = {}) => sqlite.prepare(
    "INSERT INTO works(user_id,work_key,title,first_date,last_date,times,updated_at,stage_id,stage_off) VALUES(?,?,?,?,?,1,'t',?,?)")
    .run(uid, `${titleKey(title)}#${date || 'undated'}`, title, date, date, extra.stage_id ?? null, extra.off ?? 0);
  const past = (sid, title, start, end) => sqlite.prepare(
    "INSERT INTO past_stage(stage_id,title,tkey,start,end,venue,people) VALUES(?,?,?,?,?,'本多劇場','[[\"出演\",\"山田太郎\"]]')")
    .run(sid, title, titleKey(title), start, end);
  const linkOf = (uid, title, date) => sqlite.prepare('SELECT stage_id, stage_auto FROM works WHERE user_id=? AND work_key=?')
    .get(uid, `${titleKey(title)}#${date}`);
  return {sqlite, db, work, past, linkOf};
}

test('pickStage needs the date inside exactly one run', () => {
  const s = [{stage_id: '1', start: '2023-05-10', end: '2023-05-20'}, {stage_id: '2', start: '2024-05-10', end: '2024-05-20'}];
  assert.equal(pickStage(s, '2023-05-15'), '1');
  assert.equal(pickStage(s, '2023-06-01'), '');
  assert.equal(pickStage([...s, {stage_id: '3', start: '2023-05-01', end: '2023-05-31'}], '2023-05-15'), '');
  assert.equal(pickStage([{stage_id: '4', start: '2023-05-10', end: ''}], '2023-05-10'), '4');
  assert.equal(pickStage(s, ''), '');
});

test('links a record to the one past stage with the same title on that date', async () => {
  const {db, work, past, linkOf} = setup();
  past('100', 'ハード・プロブレム', '2022-09-01', '2022-09-25');
  past('101', 'ハード・プロブレム', '2019-04-01', '2019-04-10');   // an earlier run: date says which
  work('u1', 'ハード・プロブレム', '2022-09-05');
  work('u1', 'A・NUMBER', '2022-10-07');                            // nothing to match: stays unlinked
  const made = await autoLink({db, uid: 'u1'});
  assert.deepEqual(Object.values(made), ['100']);
  assert.deepEqual({...linkOf('u1', 'ハード・プロブレム', '2022-09-05')}, {stage_id: '100', stage_auto: 1});
  assert.equal(linkOf('u1', 'A・NUMBER', '2022-10-07').stage_id, null);
});

test('never relinks a record the user unlinked, and never touches another user or a set link', async () => {
  const {db, work, past, linkOf} = setup();
  past('200', '夜の果て', '2023-03-01', '2023-03-10');
  past('201', '別の公演', '2023-03-01', '2023-03-10');
  work('u1', '夜の果て', '2023-03-05', {off: 1});
  work('u1', '別の公演', '2023-03-05', {stage_id: '999'});
  work('u2', '夜の果て', '2023-03-05');
  await autoLink({db, uid: 'u1'});
  assert.equal(linkOf('u1', '夜の果て', '2023-03-05').stage_id, null);
  assert.equal(linkOf('u1', '別の公演', '2023-03-05').stage_id, '999');
  assert.equal(linkOf('u2', '夜の果て', '2023-03-05').stage_id, null);   // only u1 was asked
  await autoLink({db, uid: 'u2'});
  assert.equal(linkOf('u2', '夜の果て', '2023-03-05').stage_id, '200');
});

test('two stages running the same title on that date are left for the user', async () => {
  const {db, work, past, linkOf} = setup();
  past('300', 'ロミオとジュリエット', '2024-08-01', '2024-08-20');
  past('301', 'ロミオとジュリエット', '2024-08-05', '2024-08-15');
  work('u1', 'ロミオとジュリエット', '2024-08-10');
  assert.deepEqual(await autoLink({db, uid: 'u1'}), {});
  assert.equal(linkOf('u1', 'ロミオとジュリエット', '2024-08-10').stage_id, null);
});
