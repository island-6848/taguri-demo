// src/screens/people.js gives people.panel(rated, owner=False)'s HTML for the same rated rows.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {panel, textW, WF, circle, sinCos, TRIG_N, build, components, timeline, readFacts, reading, readScore, READ_PICK} from '../src/screens/people.js';

const here = p => new URL(p, import.meta.url).pathname;
const fx = JSON.parse(execFileSync('python3', [here('./screens/people_fixture.py')], {encoding: 'utf8', maxBuffer: 1 << 28}));

// Compared on the characters this Python's Unicode has assigned: the table is Unicode
// 15.1.0 (Python 3.13); CI's Python 3.12 has 15.0.0, where later characters are unassigned.
test('east_asian_width W/F table matches Python unicodedata ' + fx.unidata + ' (assigned characters)', () => {
  const inside = (rs, cp) => { let lo = 0, hi = rs.length - 1; while (lo <= hi) { const m = (lo + hi) >> 1; if (cp < rs[m][0]) hi = m - 1; else if (cp > rs[m][1]) lo = m + 1; else return true; } return false; };
  const js = []; for (let i = 0; i < WF.length; i += 2) js.push([WF[i], WF[i + 1]]);
  const bad = [];
  for (let cp = 0; cp < 0x110000 && bad.length < 10; cp++) {
    if (inside(fx.unassigned, cp)) continue;
    if (inside(js, cp) !== inside(fx.wf, cp)) bad.push(cp.toString(16));
  }
  assert.deepEqual(bad, []);
  if (fx.unidata === '15.1.0') assert.deepEqual(WF, fx.wf.flat());
});

test('_text_w: ASCII, kana, half-width kana, kanji, full-width digits, astral', () => {
  for (const [s, w] of fx.text_w) assert.equal(textW(s), w, JSON.stringify(s));
});

test('starting circle: math.sin/cos(τ·i/n) for every n < TRIG_N', () => {
  const buf = Buffer.from(fx.trig, 'base64');
  const dv = new DataView(buf.buffer, buf.byteOffset, buf.byteLength);
  const bits = x => { const d = new DataView(new ArrayBuffer(8)); d.setFloat64(0, x); return d.getBigInt64(0); };
  let off = 0, bad = 0;
  const fix = [];
  for (let n = 1; n < TRIG_N; n++) {
    for (let i = 0; i < n; i++, off += 16) {
      const s = dv.getFloat64(off, true), c = dv.getFloat64(off + 8, true);
      const [js, jc] = circle(i, n);
      if (js !== s || jc !== c) bad++;
      const [rs, rc] = sinCos(2 * Math.PI * i / n);
      if (rs !== s || rc !== c) fix.push(n, i, Number(bits(s) - bits(rs)), Number(bits(c) - bits(rc)));
    }
  }
  assert.equal(off, buf.length);
  // On a mismatch, the table this Python's libm needs (paste as GLIBC_FIX).
  assert.equal(bad, 0, `GLIBC_FIX should be:\n${fix.join(', ')}`);
});

test('人のつながり matches people.panel(owner=False)', () => {
  for (const c of fx.cases) {
    const got = panel(c.rated);
    if (got !== c.html) {
      let k = 0; while (k < got.length && got[k] === c.html[k]) k++;
      assert.fail(`${c.name}: differs at ${k}\n js: ${got.slice(Math.max(0, k - 100), k + 120)}\n py: ${c.html.slice(Math.max(0, k - 100), k + 120)}`);
    }
  }
});

// ---------------------------------------------------------------- この図から分かること（規則の読み）
const factsOf = rated => {
  const g = build(rated);
  const tl = timeline(rated, g, new Map(g.core.map((p, i) => [p, i])));
  return [g, readFacts(rated, g, components(g), tl)];
};

test('読み: readFacts and reading match people.read_facts / people.reading', () => {
  for (const c of fx.cases) {
    const [, f] = factsOf(c.rated);
    assert.deepEqual(JSON.parse(JSON.stringify(f)), c.facts, c.name);
    assert.deepEqual(reading(f), c.read, c.name);
  }
});

test('読み: the panel carries the reading (and no rebuild button)', () => {
  for (const c of fx.cases) {
    if (!c.html) continue;
    assert.match(c.html, /<h3>この図から分かること<\/h3>/, c.name);
    assert.doesNotMatch(c.html, /data-pread/, c.name);
  }
});

test('読み: only names that are in the network, polite endings', () => {
  for (const c of fx.cases) {
    const [g, f] = factsOf(c.rated);
    const said = [f.top && f.top.name, f.bridge && f.bridge.name, f.pair && f.pair.a, f.pair && f.pair.b,
                  f.pair && f.pair.c, f.long && f.long.name, ...(f.recent ? f.recent.people.map(([p]) => p) : [])]
      .filter(Boolean);
    for (const p of said) assert.ok(g.nodes.includes(p), `${c.name}: ${p}`);
    for (const s of reading(f)) assert.match(s, /(です|ます|ました)。$/, `${c.name}: ${s}`);
  }
});

test('読み: the scores choose what to say', () => {
  const base = {n_core: 9, bundles: [9], top: {name: '甲', role: '出演', works: 5, splits: 0},
                bridge: null, pair: null, merge: null, started: null, recent: null, long: null,
                mix: {n: 9, makers: 2}};
  // Nothing else to say: the shape, the top person and the cast/creator mix (score 20 still > 0).
  assert.deepEqual(reading(base).length, 3);
  // A bridge that splits into 3 outranks a heavy pair of 2 works, which outranks the started line.
  const f = {...base, bridge: {name: '乙', splits: 3, people: 4}, pair: {a: '丙', b: '丁', w: 2, c: '', m: 0},
             started: {date: '2020-01-02', title: 'はじまり'}, long: {name: '戊', first: 2015, last: 2022},
             recent: {from: 2021, people: [['己', 3]]}};
  assert.equal(readScore('bridge', f), 85);
  assert.equal(readScore('pair', f), 60);
  assert.equal(readScore('long', f), 75);
  assert.equal(readScore('recent', f), 50);
  assert.equal(readScore('started', f), 30);
  const out = reading(f);
  assert.equal(out.length, 2 + READ_PICK);
  assert.match(out[2], /^乙さんを外すと、つながりが 3 つに分かれます。/);
  assert.match(out[3], /^丙さんと丁さんは 2 本で/);
  assert.match(out[4], /^戊さんは 2015 年から 2022 年まで、8 年にわたって/);
  // A merge silences the started line.
  assert.equal(readScore('started', {...f, merge: {date: '2021-01-01', title: 'x', sizes: [3, 2]}}), 0);
  // A top person who is also a bridge says so in the same sentence.
  assert.match(reading({...base, top: {...base.top, splits: 2}})[1], /外すとつながりが 2 つに分かれる人でもあります。$/);
  // No people, no reading.
  assert.deepEqual(reading({...base, top: null}), []);
});

test('読み: mix wording by the share of creators', () => {
  const f = m => reading({n_core: 10, bundles: [10], top: {name: '甲', role: '出演', works: 3, splits: 0},
    bridge: null, pair: null, merge: null, started: null, recent: null, long: null, mix: {n: 10, makers: m}}).at(-1);
  assert.match(f(0), /10 名は、みな出演者です。/);
  assert.match(f(1), /重なるのはほとんどが出演者です。/);
  assert.match(f(2), /出演が 8 名、作り手（演出・脚本ほか）が 2 名です。/);
  assert.match(f(4), /作り手の名前もよく重なっています。/);
});
