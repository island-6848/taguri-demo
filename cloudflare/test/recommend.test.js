// The Worker's recommendations must equal Python's (person-ordinal-v3).
// Python writes its answers for synthetic catalogues (test/parity_fixture.py);
// here the same index is loaded into SQLite with migration 0003 and scored
// through the same queries the Worker sends to D1.
import {DatabaseSync} from 'node:sqlite';
import {readFileSync, readdirSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {scoreFromIndex, d1Access, independentRatings, seedsFromFavourites, collapseRanked} from '../src/recommend.js';

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

// #112: the time a rating was made (rated_at) orders them before the row's last edit, in Python too.
test('ratings are ordered by rated_at, then updated_at, then the date, the same as Python', () => {
  const rows = [
    {key: 'a', stage_id: 's1', verdict: '○', rated_at: '2026-09-01 10:00:00', updated_at: '2026-09-20 10:00:00'},
    {key: 'b', stage_id: 's1', verdict: '◎', rated_at: '2026-09-05 10:00:00', updated_at: '2026-09-06 10:00:00'},
    {key: 'c', stage_id: 's2', verdict: '×', updated_at: '2026-09-03 10:00:00'},
    {key: 'd', stage_id: '', verdict: '△', date: '2026-08-01'},
  ];
  const js = independentRatings(rows).map(r => r.key);
  // s1 keeps its first slot (a, rated before c) with its latest rating (b), though a was edited last.
  assert.deepEqual(js, ['d', 'b', 'c']);
  const py = JSON.parse(execFileSync('python3', ['-c', `
import json, sys
sys.path[:0] = ['../tools/review', '../tools/taguri']
import user_recommender as UR
print(json.dumps([r["key"] for r in UR.independent_ratings(json.loads(sys.stdin.read()))]))`], {input: JSON.stringify(rows), encoding: 'utf8', stdio: ['pipe', 'pipe', 'ignore']}));
  assert.deepEqual(js, py);
});

// ---------------------------------------------------------------- through the Worker
import worker, {onboardingFor} from '../src/worker.js';
import {TERMS_VERSION} from '../src/terms.js';
const ORIGIN = 'https://taguri.example';
function envFor(sqlite) {
  const wrap = (sql, args = []) => ({bind(...v) { return wrap(sql, v); }, async first() { return sqlite.prepare(sql).get(...args) ?? null; }, async all() { return {results: sqlite.prepare(sql).all(...args)}; }, async run() { return sqlite.prepare(sql).run(...args); }, async execute() { return /^SELECT/.test(sql) ? this.all() : this.run(); }});
  return {ALLOW_REGISTRATION: 'true', DB: {prepare: sql => wrap(sql), async batch(cs) { sqlite.exec('BEGIN'); try { const r = []; for (const c of cs) r.push(await c.execute()); sqlite.exec('COMMIT'); return r; } catch (e) { sqlite.exec('ROLLBACK'); throw e; } }}, ASSETS: {fetch: () => new Response('')}};
}
const call = (env, path, value, cookie = '') => worker.fetch(new Request(`${ORIGIN}/migration-api/${path}`, value === undefined ? {headers: {cookie}} : {method: 'POST', headers: {cookie, origin: ORIGIN, 'content-type': 'application/json'}, body: JSON.stringify(value)}), env);

// One slot per production, as Python's collapse_tours (build_recommend_index.collapse_ranked).
// GET /api/recommend no longer computes from the migration-era records (#119: it answers with the
// 今週のおすすめ screen's ranking, test/recommend-screen.test.js), so the Python parity of the
// scoring is checked on scoreFromIndex above and of the grouping here.
test('one slot per tour, the first 15, as Python', () => {
  let checked = 0, toursSeen = 0;
  for (const cat of fixture.catalogues) for (const c of cat.cases) {
    const want = c.listed || c.listed_after_first;
    const got = collapseRanked(c.listed ? c.expected : c.expected.slice(1), 15);
    assert.deepEqual(got.map(g => [g.stage_id, g.tours]), want.map(g => [g.stage_id, g.tours]));
    checked++; toursSeen += got.some(g => g.tours.length);
  }
  assert.equal(checked, 144 + 24);
  assert.ok(toursSeen >= 2, `listings with a tour: ${toursSeen}`);
});

test('the first stages to ask about: favourites already on, then the batch list, minus recorded ones', async () => {
  let checked = 0;
  for (const cat of fixture.catalogues.slice(0, 6)) {
    const c = cat.cases.find(x => x.favourites);
    const sqlite = load(cat), env = envFor(sqlite);
    const cookie = (await call(env, 'register', {agree: TERMS_VERSION})).headers.get('set-cookie').split(';')[0];
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
  const cookie = (await call(env, 'register', {agree: TERMS_VERSION})).headers.get('set-cookie').split(';')[0];
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
  const cookie = (await call(env, 'register', {agree: TERMS_VERSION})).headers.get('set-cookie').split(';')[0];
  assert.deepEqual(await (await call(env, 'recommend', undefined, cookie)).json(), {ready: false, items: []});
  assert.equal((await call(env, 'record', {title: 'x', date: '2026-01-01', stage_id: '../x'}, cookie)).status, 400);
});
