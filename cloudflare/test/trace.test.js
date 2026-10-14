// src/screens/trace.js gives trace.body's HTML for the same rated rows.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {body} from '../src/screens/trace.js';

const here = p => new URL(p, import.meta.url).pathname;
const fx = JSON.parse(execFileSync('python3', [here('./screens/trace_fixture.py')], {encoding: 'utf8'}));

test('たどる matches trace.body', () => {
  for (const c of fx.cases) {
    const got = body(fx.rated, c.name, c.via, c.declared);
    if (got !== c.html) {
      let k = 0; while (k < got.length && got[k] === c.html[k]) k++;
      assert.fail(`${c.name}: differs at ${k}\n js: ${got.slice(Math.max(0, k - 100), k + 120)}\n py: ${c.html.slice(Math.max(0, k - 100), k + 120)}`);
    }
  }
});
