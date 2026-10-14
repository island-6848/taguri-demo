// The Worker's recommendations must equal Python's (person-ordinal-v3).
// Python writes its answers for synthetic catalogues (test/parity_fixture.py);
// here the same index is loaded into SQLite with migration 0003 and scored
// through the same queries the Worker sends to D1.
import {DatabaseSync} from 'node:sqlite';
import {readFileSync, readdirSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {scoreFromIndex, d1Access, independentRatings, seedsFromFavourites} from '../src/recommend.js';

const fixture = JSON.parse(execFileSync('python3', [new URL('./parity_fixture.py', import.meta.url).pathname], {maxBuffer: 256 * 1024 * 1024, encoding: 'utf8'}));

function d1(sqlite) {
  const wrap = (sql, args = []) => ({bind(...v) { return wrap(sql, v); }, async first() { return sqlite.prepare(sql).get(...args) ?? null; }, async all() { return {results: sqlite.prepare(sql).all(...args)}; }, async run() { return sqlite.prepare(sql).run(...args); }});
  return {prepare: sql => wrap(sql)};
}
function load(cat) {
  const sqlite = new DatabaseSync(':memory:');
  for (const f of readdirSync(new URL('../migrations/', import.meta.url)).filter(n => n.endsWith('.sql')).sort()) sqlite.exec(readFileSync(new URL(`../migrations/${f}`, import.meta.url), 'utf8'));
  for (const stmt of cat.sql) sqlite.exec(stmt);
  return sqlite;
}

test('JS scores equal Python for every catalogue, history and weight setting', async () => {
  let compared = 0, nonEmpty = 0, rowsRead = 0, seeded = 0;
  for (const cat of fixture.catalogues) {
    const sqlite = load(cat);
    for (const c of cat.cases) {
      const access = d1Access(d1(sqlite), cat.ver);
      const {seeds, skip} = c.favourites ? await seedsFromFavourites(access, c.favourites) : {};
      if (c.favourites) { assert.deepEqual(seeds.map(s => s.stage_id), c.seeds); seeded += seeds.length > 0; }
      const got = await scoreFromIndex({...access, rated: c.rated, multipliers: c.multipliers, today: fixture.today, seeds, skip});
      assert.deepStrictEqual(got, c.expected, `seed ${cat.seed}, weights ${JSON.stringify(c.multipliers)}${c.favourites ? ', favourites' : ''}`);
      compared++; nonEmpty += c.expected.length > 0; rowsRead += access.counter.rows;
    }
    sqlite.close();
  }
  assert.equal(compared, 144 + 24);
  assert.ok(seeded >= 18, `favourites found seed stages in ${seeded} of 24 cases`);
  assert.ok(nonEmpty > compared / 2, 'the comparison must not pass vacuously');
});

test('only the latest rating per linked stage counts; unlinked records stay separate', () => {
  const rows = [
    {key: 'a', stage_id: 's1', verdict: '○', updated_at: '2026-09-01 10:00:00'},
    {key: 'b', stage_id: 's1', verdict: '◎', updated_at: '2026-09-05 10:00:00'},
    {key: 'c', stage_id: '', verdict: '×', date: '2026-08-01'},
    {key: 'd', stage_id: '', verdict: '', date: '2026-08-02'},
  ];
  assert.deepEqual(independentRatings(rows).map(r => r.key), ['c', 'b']);
});

// ---------------------------------------------------------------- through the Worker
import worker, {recommendFor, onboardingFor} from '../src/worker.js';
const ORIGIN = 'https://taguri.example';
function envFor(sqlite) {
  const wrap = (sql, args = []) => ({bind(...v) { return wrap(sql, v); }, async first() { return sqlite.prepare(sql).get(...args) ?? null; }, async all() { return {results: sqlite.prepare(sql).all(...args)}; }, async run() { return sqlite.prepare(sql).run(...args); }, async execute() { return /^SELECT/.test(sql) ? this.all() : this.run(); }});
  return {ALLOW_REGISTRATION: 'true', DB: {prepare: sql => wrap(sql), async batch(cs) { sqlite.exec('BEGIN'); try { const r = []; for (const c of cs) r.push(await c.execute()); sqlite.exec('COMMIT'); return r; } catch (e) { sqlite.exec('ROLLBACK'); throw e; } }}, ASSETS: {fetch: () => new Response('')}};
}
const call = (env, path, value, cookie = '') => worker.fetch(new Request(`${ORIGIN}/migration-api/${path}`, value === undefined ? {headers: {cookie}} : {method: 'POST', headers: {cookie, origin: ORIGIN, 'content-type': 'application/json'}, body: JSON.stringify(value)}), env);

test('records saved through the API give the same recommendations as Python, minus reacted stages', async () => {
  let checked = 0, toursSeen = 0;
  for (const cat of fixture.catalogues.slice(0, 6)) {
    for (const c of cat.cases.filter(x => !x.favourites && Object.keys(x.multipliers).length === 0 && x.expected.length >= 3)) {
      const sqlite = load(cat), env = envFor(sqlite);
      const reg = await call(env, 'register', {});
      const cookie = reg.headers.get('set-cookie').split(';')[0];
      const uid = sqlite.prepare('SELECT id FROM users').get().id;
      for (const r of c.rated) {
        const res = await call(env, 'record', {id: r.key, title: r.key, date: r.date, rating: r.verdict, stage_id: r.stage_id, aspects: r.aspects}, cookie);
        assert.equal(res.status, 200, await res.text());
        // Keep Python's order of rating times (latest rating of a stage wins).
        sqlite.prepare('UPDATE records SET updated_at=? WHERE user_id=? AND id=?').run(Date.parse(r.updated_at.replace(' ', 'T') + 'Z') / 1000, uid, r.key);
      }
      const reacted = c.expected[0].stage_id;
      await call(env, 'reaction', {stage_id: reacted, status: 'no'}, cookie);
      const got = await recommendFor(env.DB, uid, fixture.today);
      // One slot per tour, as Python's collapse_tours (collapse_ranked).
      const byId = new Map(c.expected.map(x => [x.stage_id, x]));
      const want = c.listed_after_first;
      assert.equal(got.ready, true);
      assert.equal(got.variant, 'base', 'few ratings: the hidden check keeps the default rules');
      assert.deepEqual(got.items.map(i => [i.stage_id, i.score, i.tours.map(t => t.stage_id)]), want.map(g => [g.stage_id, byId.get(g.stage_id).b, g.tours]));
      assert.deepEqual(got.items[0].reasons, byId.get(want[0].stage_id).parts.slice(0, 3).map(([, role, person, n]) => ({role, person, n})));
      toursSeen += got.items.some(i => i.tours.length);
      assert.ok(got.items.every(i => i.tours.every(t => t.theater)), 'tour venues carry their display fields');
      assert.ok(got.items.every(i => i.title), 'display fields come from rec_stage');
      // The cache is keyed by the scoring rules too (a rule change recomputes).
      assert.ok(sqlite.prepare('SELECT stamp FROM rec_cache WHERE user_id=?').get(uid).stamp.startsWith('person-ordinal-v3+fav1+asp1+tour1|'));
      // Second view: served from the cache, same answer.
      const again = await recommendFor(env.DB, uid, fixture.today);
      assert.equal(again.cached, true);
      assert.deepEqual(again.items, got.items);
      // A new rating, a reaction, a new day or a new index version recomputes.
      await call(env, 'reaction', {stage_id: got.items[0].stage_id, status: 'interest'}, cookie);
      const afterReaction = await recommendFor(env.DB, uid, fixture.today);
      assert.equal(afterReaction.cached, false);
      assert.ok(!afterReaction.items.some(i => i.stage_id === got.items[0].stage_id));
      assert.equal((await recommendFor(env.DB, uid, '2026-10-13')).cached, false);
      // Two changes within the same second still recompute.
      await recommendFor(env.DB, uid, fixture.today);
      sqlite.prepare('UPDATE reactions SET updated_at=0 WHERE user_id=?').run(uid);
      await recommendFor(env.DB, uid, fixture.today);
      await call(env, 'reaction', {stage_id: got.items[0].stage_id, status: 'owned'}, cookie);   // same count, same time
      sqlite.prepare('UPDATE reactions SET updated_at=0 WHERE user_id=?').run(uid);
      assert.equal((await recommendFor(env.DB, uid, fixture.today)).cached, false);
      checked++;
      sqlite.close();
    }
  }
  assert.ok(checked >= 5, `checked ${checked}`);
  assert.ok(toursSeen >= 2, `listings with a tour: ${toursSeen}`);
});

test('favourites give recommendations before any rating, as Python, and fade as ratings come in', async () => {
  let checked = 0;
  for (const cat of fixture.catalogues.slice(0, 6)) {
    const c = cat.cases.find(x => x.favourites && !x.rated.length && x.expected.length >= 3);
    if (!c) continue;
    const sqlite = load(cat), env = envFor(sqlite);
    const cookie = (await call(env, 'register', {})).headers.get('set-cookie').split(';')[0];
    const uid = sqlite.prepare('SELECT id FROM users').get().id;
    assert.equal((await recommendFor(env.DB, uid, fixture.today)).items.length, 0, 'nothing to go on yet');
    for (const f of c.favourites) assert.equal((await call(env, 'favourite', f, cookie)).status, 200);
    const got = await recommendFor(env.DB, uid, fixture.today);
    assert.equal(got.cached, false, 'adding a favourite drops the cached result');
    assert.equal(got.n_seeds, c.seeds.length);
    const byId = new Map(c.expected.map(x => [x.stage_id, x]));
    assert.deepEqual(got.items.map(i => [i.stage_id, i.score, i.tours.map(t => t.stage_id)]), c.listed.map(g => [g.stage_id, byId.get(g.stage_id).b, g.tours]));
    // The favourites' own shows are listed elsewhere, not recommended here.
    assert.ok(!got.items.some(i => c.seeds.includes(i.stage_id)));
    checked++;
    sqlite.close();
  }
  assert.ok(checked >= 3, `checked ${checked}`);
});

test('the first stages to ask about: favourites already on, then the batch list, minus recorded ones', async () => {
  let checked = 0;
  for (const cat of fixture.catalogues.slice(0, 6)) {
    const c = cat.cases.find(x => x.favourites);
    const sqlite = load(cat), env = envFor(sqlite);
    const cookie = (await call(env, 'register', {})).headers.get('set-cookie').split(';')[0];
    const uid = sqlite.prepare('SELECT id FROM users').get().id;
    const plain = await onboardingFor(env.DB, uid, fixture.today);
    assert.deepEqual(plain.items.map(i => i.stage_id), cat.onboarding.slice(0, 20));
    assert.ok(plain.items.every(i => i.because === 'catalogue' && i.title && i.start <= fixture.today));
    const res = await call(env, 'onboarding', undefined, cookie);
    assert.equal(res.status, 200);
    for (const f of c.favourites) await call(env, 'favourite', f, cookie);
    const withFav = await onboardingFor(env.DB, uid, fixture.today);
    const favFirst = withFav.items.filter(i => i.because === 'favourite').map(i => i.stage_id);
    assert.deepEqual(withFav.items.slice(0, favFirst.length).map(i => i.stage_id), favFirst, 'favourites come first');
    const names = c.favourites.filter(f => ['人', '原作者'].includes(f.kind)).map(f => f.name);
    for (const sid of favFirst) assert.ok(sqlite.prepare(`SELECT 1 FROM rec_credit WHERE stage_id=? AND person IN (${names.map(() => '?').join(',')})`).get(sid, ...names), sid);
    checked += favFirst.length > 0;
    // A recorded stage is not asked about again.
    const first = withFav.items[0].stage_id;
    await call(env, 'record', {id: 'r1', title: 't', date: fixture.today, rating: '', stage_id: first}, cookie);
    assert.ok(!(await onboardingFor(env.DB, uid, fixture.today)).items.some(i => i.stage_id === first));
    // A list built for another index version is not used.
    sqlite.prepare("UPDATE rec_meta SET v=? WHERE k='onboarding'").run(JSON.stringify({ver: 'old', ids: cat.onboarding}));
    assert.ok((await onboardingFor(env.DB, uid, fixture.today)).items.every(i => i.because === 'favourite'));
    sqlite.close();
  }
  assert.ok(checked >= 2, `favourites' stages found for ${checked} catalogues`);
});

test('詳細 are saved as known codes (troubles, then "+goods") in a fixed order, and anything else is refused', async () => {
  const cat = fixture.catalogues[0];
  const sqlite = load(cat), env = envFor(sqlite);
  const cookie = (await call(env, 'register', {})).headers.get('set-cookie').split(';')[0];
  const base = {id: 'a1', title: 't', date: '2026-09-01', rating: '2/5'};
  const saved = () => sqlite.prepare("SELECT aspects FROM records WHERE id='a1'").get().aspects;
  assert.equal((await call(env, 'record', {...base, aspects: ['+acting', 'venue', 'price']}, cookie)).status, 200);
  assert.equal(saved(), 'price,venue,+acting');
  // The text form /api/state returns is accepted back.
  assert.equal((await call(env, 'record', {...base, aspects: '+acting,price'}, cookie)).status, 200);
  assert.equal(saved(), 'price,+acting');
  for (const bad of [['もやもや'], ['+もやもや'], ['acting', '+acting'], 7, [7]])
    assert.equal((await call(env, 'record', {...base, aspects: bad}, cookie)).status, 400, JSON.stringify(bad));
  assert.equal((await call(env, 'record', base, cookie)).status, 200);
  assert.equal(saved(), '');
  sqlite.close();
});

test('the API needs sign-in, and says when the index is not built yet', async () => {
  const sqlite = new DatabaseSync(':memory:');
  for (const f of readdirSync(new URL('../migrations/', import.meta.url)).filter(n => n.endsWith('.sql')).sort()) sqlite.exec(readFileSync(new URL(`../migrations/${f}`, import.meta.url), 'utf8'));
  const env = envFor(sqlite);
  assert.equal((await call(env, 'recommend')).status, 401);
  const cookie = (await call(env, 'register', {})).headers.get('set-cookie').split(';')[0];
  assert.deepEqual(await (await call(env, 'recommend', undefined, cookie)).json(), {ready: false, items: []});
  assert.equal((await call(env, 'record', {title: 'x', date: '2026-01-01', stage_id: '../x'}, cookie)).status, 400);
});
