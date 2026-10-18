// 感想の好み（src/impression.js）は Python（tools/review/impression_preferences.py）と同じ答えを返す（issue #104）。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {extract, buildProfile, score} from '../src/impression.js';

const here = p => new URL(p, import.meta.url).pathname;
const PY = JSON.parse(execFileSync('python3', [here('./screens/impression_fixture.py')], {encoding: 'utf8'}));

test('signals from each impression match Python', () => {
  for (const c of PY.extract) assert.deepEqual(extract(c.note, PY.works[0].elements), c.signals, c.note);
});

test('the profile (one vote per work and feature) and the candidate adjustment match Python', () => {
  const profile = buildProfile(PY.works);
  const got = Object.fromEntries([...profile].sort(([a], [b]) => (a < b ? -1 : 1))
    .map(([k, v]) => [k, {weight: v.weight, count: v.count, keys: v.evidence.map(e => e.work_key)}]));
  assert.deepEqual(got, PY.profile);
  for (const c of PY.score) {
    const [adj, parts] = score(c.elements, profile);
    assert.equal(adj, c.result[0]);
    assert.deepEqual(parts, c.result[1]);
  }
});

test('a positive and a negative note move the same feature in opposite directions; no note changes nothing', () => {
  const el = [{word: '家族'}];
  const w = note => buildProfile([{work_key: 'x', note_impression: note, elements: el}]);
  assert.ok(score(el, w('家族の描写が好き'))[0] > 0);
  assert.ok(score(el, w('家族の描写が苦手'))[0] < 0);
  assert.equal(score(el, w(''))[0], 0);
});
