// src/screens/chronicle.js gives chronicle.panel's HTML for the same records, and
// chronicle.reading's text for the same facts (test/screens/chronicle_fixture.py).
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {panel, facts, reading} from '../src/screens/chronicle.js';

const here = p => new URL(p, import.meta.url).pathname;
const {cases, readings, star_cases: starCases} = JSON.parse(execFileSync('python3', [here('./screens/chronicle_fixture.py')], {encoding: 'utf8'}));

test('観劇史年表 matches chronicle.panel', () => {
  cases.forEach((c, i) => {
    const got = panel(c.works, c.rated);
    if (got !== c.html) {
      let k = 0; while (k < got.length && got[k] === c.html[k]) k++;
      assert.fail(`case ${i}: differs at ${k}\n js: ${got.slice(Math.max(0, k - 100), k + 120)}\n py: ${c.html.slice(Math.max(0, k - 100), k + 120)}`);
    }
  });
});

test('観劇史年表: the reading from the records matches chronicle.reading', () => {
  cases.forEach((c, i) => assert.deepEqual(reading(facts(c.works, c.rated)), c.reading, `case ${i}`));
});

test('観劇史年表: the reading from the facts (with themes) matches chronicle.reading', () => {
  readings.forEach((c, i) => assert.deepEqual(reading(c.facts), c.reading, `reading ${i}`));
});

test('観劇史年表: a star user\'s top and low grades are counted as in Python (issue #177)', () => {
  starCases.forEach((c, i) => {
    const f = facts(c.works, c.rated);
    for (const k of ['n_loved', 'n_hard']) assert.equal(f[k], c.facts[k], `${k} ${i}`);
    assert.deepEqual(f.years.map(y => [y.loved, y.hard, y.new_people]), c.facts.years.map(y => [y.loved, y.hard, y.new_people]), `years ${i}`);
    assert.ok(f.n_loved > 0);
    assert.deepEqual(reading(f), c.reading, `reading ${i}`);
  });
});

test('観劇史年表: the #題材 words of the stages seen become the year\'s themes, without the names in the credits (issue #177)', () => {
  const ws = [1, 2, 3].map(i => ({work_key: `t${i}`, title: `作${i}`, first_date: `2024-0${i}-01`, verdict: '○'}));
  const rated = [{key: 't1', people: [['原作', 'シェイクスピア']], venues: [], themes: ['家族', 'シェイクスピア']},
    {key: 't2', people: [], venues: [], themes: ['家族', '法廷']}, {key: 't3', people: [], venues: [], themes: ['家族']}];
  const f = facts(ws, rated);
  assert.deepEqual(f.years[0].themes, [['家族', 3], ['法廷', 1]]);
  assert.deepEqual(f.overall_themes, [['家族', 3], ['法廷', 1]]);
  assert.deepEqual(f.years[0].tone, []);
});

// ---------------------------------------------------------------- the rules
const eras = readings[0];          // 帝国劇場の 2 年 → 3 年あいて本多劇場の 2 年（家族 → 法廷）

test('観劇史年表: eras split where 2 or more things change in the same year', () => {
  const r = reading(eras.facts);
  assert.deepEqual(r.eras.map(e => [e.from, e.to]), [['2018', '2019'], ['2022', '2023']]);
  assert.equal(r.eras[0].name, '帝国劇場に通っていた 2 年');
  assert.equal(r.eras[1].name, '本多劇場に通う 2 年');
  assert.match(r.eras[1].body, /通う先は帝国劇場から本多劇場へ移りました。/);
  assert.match(r.eras[1].body, /題材は家族から法廷へ移っています。/);
  // one record a year with nothing changing: one era
  const flat = facts([1, 2, 3].map(i => ({work_key: `f${i}`, title: `作${i}`, first_date: `202${i}-01-01`, verdict: '○'})),
    [1, 2, 3].map(i => ({key: `f${i}`, venues: ['同じ劇場'], people: []})));
  assert.equal(reading(flat).eras.length, 1);
});

test('観劇史年表: a line for every year, led by the gap or the start', () => {
  const r = reading(eras.facts);
  assert.deepEqual(Object.keys(r.years), ['2018', '2019', '2022', '2023']);
  assert.match(r.years['2018'], /^記録はこの年から始まります。/);
  assert.match(r.years['2022'], /^2019 年以来、3 年ぶりに観た年です。丙と出会い/);
  for (const line of Object.values(r.years)) assert.ok(Array.from(line).length <= 70, line);
});

test('観劇史年表: the closing gives the direction from the first era to the last', () => {
  assert.equal(reading(eras.facts).closing,
    '通う先は帝国劇場から本多劇場へ移り、観る本数は年を追って増えています。題材は家族から法廷へ移っています。');
  assert.equal(reading(facts([], [])).closing, '');
});

test('観劇史年表: no name that is not in the facts', () => {
  for (const c of readings) {
    const f = c.facts, have = new Set();
    for (const y of f.years) {
      for (const [v] of y.venues) have.add(v);
      for (const v of y.new_venues) have.add(v);
      for (const [nm] of [...y.people, ...y.new_people]) have.add(nm);
      for (const t of [...y.loved, ...y.hard, ...y.repeats.map(x => x[0])]) have.add(t);
      for (const [w] of [...y.themes, ...y.tone]) have.add(w);
    }
    for (const [v] of [...f.kept_venues, ...f.left_venues]) have.add(v);
    for (const [, nm] of f.long_people) have.add(nm);
    for (const [w] of [...f.overall_themes, ...f.overall_tone]) have.add(w);
    const r = reading(f);
    for (const e of r.eras) for (const x of e.evidence) assert.ok(have.has(x), x);
    for (const x of (r.profile.evidence || [])) assert.ok(have.has(x), x);
    // every 「題名」 quoted in the text is a title in the facts
    const text = JSON.stringify(r);
    for (const m of text.matchAll(/「([^」]+)」/g)) assert.ok(have.has(m[1]), m[1]);
  }
});
