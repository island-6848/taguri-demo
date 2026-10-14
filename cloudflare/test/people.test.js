// src/screens/people.js gives people.panel(rated, owner=False)'s HTML for the same rated rows.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {panel, textW, WF, circle, sinCos, TRIG_N} from '../src/screens/people.js';

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
