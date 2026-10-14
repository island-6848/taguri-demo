// src/screens/weights.js gives app.weight_form's HTML and the same steps and groups.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {weightForm, WEIGHT_STEPS, ROLE_GROUPS} from '../src/screens/weights.js';

const here = p => new URL(p, import.meta.url).pathname;
const fx = JSON.parse(execFileSync('python3', [here('./screens/weights_fixture.py')], {encoding: 'utf8'}));

test('steps and groups are app.WEIGHT_STEPS and app.ROLE_GROUPS', () => {
  assert.deepEqual(WEIGHT_STEPS, fx.steps);
  assert.deepEqual(ROLE_GROUPS, fx.groups);
});

test('おすすめの効かせ方 matches app.weight_form', () => {
  for (const c of fx.cases) {
    const got = weightForm(c.w, c.cnt, c.drop);
    if (got !== c.html) {
      let k = 0; while (k < got.length && got[k] === c.html[k]) k++;
      assert.fail(`differs at ${k}\n js: ${got.slice(Math.max(0, k - 80), k + 100)}\n py: ${c.html.slice(Math.max(0, k - 80), k + 100)}`);
    }
  }
});
