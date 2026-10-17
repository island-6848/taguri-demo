// Linking a record to a stage: the Worker's title search must equal Python's
// search_index (scripts/build_recommend_index.py) on the same index, and its
// query normalisation must equal rate_performances.title_key.
import {DatabaseSync} from 'node:sqlite';
import {readFileSync, readdirSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {titleKey, searchIndex, d1Search} from '../src/stage-search.js';
import worker from '../src/worker.js';
import {TERMS_VERSION} from '../src/terms.js';

const fixture = JSON.parse(execFileSync('python3', [new URL('./parity_fixture.py', import.meta.url).pathname], {maxBuffer: 256 * 1024 * 1024, encoding: 'utf8'}));
const migrations = sqlite => { for (const f of readdirSync(new URL('../migrations/', import.meta.url)).filter(n => n.endsWith('.sql')).sort()) sqlite.exec(readFileSync(new URL(`../migrations/${f}`, import.meta.url), 'utf8')); };
function d1(sqlite) {
  const wrap = (sql, args = []) => ({bind(...v) { return wrap(sql, v); }, async first() { return sqlite.prepare(sql).get(...args) ?? null; }, async all() { return {results: sqlite.prepare(sql).all(...args)}; }, async run() { return sqlite.prepare(sql).run(...args); }, async execute() { return /^SELECT/.test(sql) ? this.all() : this.run(); }});
  return {prepare: sql => wrap(sql), async batch(cs) { sqlite.exec('BEGIN'); try { const r = []; for (const c of cs) r.push(await c.execute()); sqlite.exec('COMMIT'); return r; } catch (e) { sqlite.exec('ROLLBACK'); throw e; } }};
}
function load(cat) {
  const sqlite = new DatabaseSync(':memory:');
  migrations(sqlite);
  for (const stmt of cat.sql) sqlite.exec(stmt);
  return sqlite;
}

test('the query is normalised exactly like title_key', () => {
  let differ = 0;
  for (const [title, key] of fixture.title_keys) if (titleKey(title) !== key) { differ++; assert.equal(titleKey(title), key, JSON.stringify(title)); }
  assert.equal(differ, 0);
  assert.ok(fixture.title_keys.length > 3000);
});

test('search results equal Python for every catalogue, query and date', async () => {
  let compared = 0, found = 0, rows = 0;
  for (const cat of fixture.catalogues) {
    const sqlite = load(cat);
    for (const s of cat.searches) {
      const access = d1Search(d1(sqlite), cat.ver);
      assert.deepStrictEqual(await searchIndex(access.entriesFor, s.q, s.date), s.expected, `seed ${cat.seed} ${s.q} ${s.date}`);
      compared++; found += s.expected.length > 0; rows += access.counter.rows;
    }
    sqlite.close();
  }
  assert.ok(found > compared / 3, `${found}/${compared}`);
});

const ORIGIN = 'https://taguri.example';
const env = db => ({ALLOW_REGISTRATION: 'true', DB: db, ASSETS: {fetch: () => new Response('')}});
const get = (e, path, cookie = '') => worker.fetch(new Request(`${ORIGIN}/migration-api/${path}`, {headers: {cookie}}), e);
const post = (e, path, value, cookie = '') => worker.fetch(new Request(`${ORIGIN}/migration-api/${path}`, {method: 'POST', headers: {cookie, origin: ORIGIN, 'content-type': 'application/json'}, body: JSON.stringify(value)}), e);

test('the API searches and names linked stages, with display fields only', async () => {
  const cat = fixture.catalogues[0], sqlite = load(cat), e = env(d1(sqlite));
  assert.equal((await get(e, 'stages?q=舞台')).status, 401);
  const cookie = (await post(e, 'register', {agree: TERMS_VERSION})).headers.get('set-cookie').split(';')[0];
  const s = cat.searches.find(x => x.expected.length >= 2 && x.date);
  const res = await (await get(e, `stages?q=${encodeURIComponent(s.q)}&date=${s.date}`, cookie)).json();
  assert.equal(res.ready, true);
  assert.deepEqual(res.items.map(i => i.stage_id), s.expected);
  const row = sqlite.prepare('SELECT title,grp,start,end,entry FROM rec_stage WHERE ver=? AND stage_id=?').get(cat.ver, s.expected[0]);
  const entry = JSON.parse(row.entry);
  assert.deepEqual(res.items[0], {stage_id: s.expected[0], title: row.title, group: row.grp, start: row.start, end: row.end, theater: entry.theater || '', pref: entry.pref || '', url: entry.url || ''});
  assert.ok(res.items.every(i => !('credits' in i) && !('entry' in i)), 'only display fields');
  // Names of linked stages, in the asked order; unknown ids are left out.
  const named = await (await get(e, `stages?ids=${s.expected[1]},nope,${s.expected[0]}`, cookie)).json();
  assert.deepEqual(named.items.map(i => i.stage_id), [s.expected[1], s.expected[0]]);
  // Bad input.
  for (const bad of ['stages?ids=../x', `stages?ids=${Array.from({length: 101}, (_, i) => 'a' + i).join(',')}`, `stages?q=${'あ'.repeat(101)}`, 'stages?q=舞台&date=today'])
    assert.equal((await get(e, bad, cookie)).status, 400, bad);
  assert.deepEqual((await (await get(e, 'stages?q=台', cookie)).json()).items, []);
  sqlite.close();
});

test('before the index is uploaded the search says so', async () => {
  const sqlite = new DatabaseSync(':memory:');
  migrations(sqlite);
  const e = env(d1(sqlite));
  const cookie = (await post(e, 'register', {agree: TERMS_VERSION})).headers.get('set-cookie').split(';')[0];
  assert.deepEqual(await (await get(e, 'stages?q=舞台', cookie)).json(), {ready: false, items: []});
});
