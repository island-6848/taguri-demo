// src/screens/compare.js gives compare.pop_note's and compare.panel's (作りの型) HTML,
// and keeps the D1 count of the comparison set to one a day.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync, readdirSync} from 'node:fs';
import {CRAFTS, panel, popNote, population, rows, craftRows} from '../src/screens/compare.js';

const here = p => new URL(p, import.meta.url).pathname;
const fx = JSON.parse(execFileSync('python3', [here('./screens/compare_fixture.py')], {encoding: 'utf8'}));

function same(got, want, what) {
  if (got === want) return;
  let k = 0; while (k < got.length && got[k] === want[k]) k++;
  assert.fail(`${what}: differs at ${k}\n js: ${got.slice(Math.max(0, k - 100), k + 120)}\n py: ${want.slice(Math.max(0, k - 100), k + 120)}`);
}

test('比べる相手は何か matches compare.pop_note', () => {
  fx.pop.forEach((c, i) => same(popNote(c.rated, c.pop), c.html, `pop ${i}`));
});

test('作りの型 matches compare.panel', () => {
  const labels = CRAFTS.map(c => c[1]);
  fx.craft.forEach((c, i) => same(panel({craft: [rows(labels, c.mine, c.world, c.nMine, c.nWorld), c.nMine, c.nWorld]}), c.html, `craft ${i}`));
});

function d1() {
  const db = new DatabaseSync(':memory:');
  const dir = here('../migrations/');
  for (const f of readdirSync(dir).filter(f => f.endsWith('.sql')).sort()) db.exec(readFileSync(dir + f, 'utf8'));
  let reads = 0;
  const wrap = sql => {
    const st = db.prepare(sql); let args = [];
    const o = {bind: (...a) => { args = a; return o; },
      first: async () => { reads++; return st.get(...args) ?? null; },
      all: async () => { reads++; return {results: st.all(...args)}; }, run: async () => st.run(...args)};
    return o;
  };
  return {db, d: {prepare: wrap}, reads: () => reads};
}

test('the comparison set is counted once a day, from rec_stage, rec_credit and catalogue', async () => {
  const {db, d, reads} = d1();
  db.exec("INSERT INTO rec_meta VALUES('current','v1')");
  const st = (id, s, e) => db.prepare("INSERT INTO rec_stage(ver,stage_id,title,start,end) VALUES('v1',?,?,?,?)").run(id, id, s, e);
  st('a', '2026-10-01', '2026-10-30'); st('b', '2026-11-01', '2026-11-05'); st('c', '2026-09-01', '2026-10-01'); st('d', '', '');
  const cr = (role, p, s) => db.prepare("INSERT INTO rec_credit VALUES('v1',?,?,?,1,'x')").run(role, p, s);
  cr('翻訳', '甲', 'a'); cr('翻訳', '乙', 'a'); cr('翻訳', '甲', 'b'); cr('振付', '丙', 'c'); cr('出演', '丁', 'a');
  db.exec("INSERT INTO catalogue(id,title,date) VALUES('x','t','2026-10-01'),('y','t','2026-10-02')");
  const p = await population(d, '2026-10-14');
  assert.deepEqual({...p, stamp: undefined}, {stamp: undefined, n: 4, n_upcoming: 1, n_running: 1, n_ended: 1,
    first: '2026-09-01', last: '2026-11-01', other: 2, crafts: {翻訳: 2, 振付: 1}});
  const before = reads();
  assert.deepEqual(await population(d, '2026-10-14'), p);
  assert.equal(reads() - before, 2, 'the second view reads only the version and the kept answer');
  assert.notEqual((await population(d, '2026-10-15')).stamp, p.stamp);
  const [rs, nm, nw] = craftRows([{people: [['翻訳', '甲'], ['出演', '乙']]}, {people: [['出演', '乙']]}, {people: []}], p);
  assert.equal(nm, 2); assert.equal(nw, 4);
  assert.deepEqual(rs.map(r => [r.label.slice(0, 3), r.n, r.n_pop]), [['翻訳劇', 1, 2], ['振付つ', 0, 1], ['音楽劇', 0, 0], ['原作つ', 0, 0]]);
});
