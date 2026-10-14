// src/screens/chronicle.js gives chronicle.panel(owner=False)'s HTML for the same records.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {panel} from '../src/screens/chronicle.js';

const here = p => new URL(p, import.meta.url).pathname;
const cases = JSON.parse(execFileSync('python3', [here('./screens/chronicle_fixture.py')], {encoding: 'utf8'}));

test('観劇史年表 matches chronicle.panel', () => {
  cases.forEach((c, i) => {
    const got = panel(c.works, c.rated);
    if (got !== c.html) {
      let k = 0; while (k < got.length && got[k] === c.html[k]) k++;
      assert.fail(`case ${i}: differs at ${k}\n js: ${got.slice(Math.max(0, k - 100), k + 120)}\n py: ${c.html.slice(Math.max(0, k - 100), k + 120)}`);
    }
  });
});
