// src/screens/storyline.js gives storyline.panel's HTML for the same rated rows.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {panel} from '../src/screens/storyline.js';

const here = p => new URL(p, import.meta.url).pathname;
const fx = JSON.parse(execFileSync('python3', [here('./screens/storyline_fixture.py')], {encoding: 'utf8', maxBuffer: 1 << 26}));

test('人の流れ matches storyline.panel', () => {
  fx.cases.forEach((c, i) => {
    const got = panel(c.rated, c.min_times);
    if (got !== c.html) {
      let k = 0; while (k < got.length && got[k] === c.html[k]) k++;
      assert.fail(`case ${i} (min_times ${c.min_times}): differs at ${k}\n js: ${got.slice(Math.max(0, k - 100), k + 120)}\n py: ${c.html.slice(Math.max(0, k - 100), k + 120)}`);
    }
  });
});
