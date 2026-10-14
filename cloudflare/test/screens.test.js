// The original screens ported to the Worker (src/screens/) must answer exactly
// as the Python app on Render does. test/screens/python_screens.py runs each
// scenario in test/screens/scenarios.json on the Python app; here the same
// steps run on the Worker (NATIVE_UI=all) with a fresh signed-in account.
import {readFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {setup, step, signIn} from './screens/harness.js';

const here = p => new URL(p, import.meta.url).pathname;
const scenarios = JSON.parse(readFileSync(here('./screens/scenarios.json'), 'utf8'));
const python = JSON.parse(execFileSync('python3', [here('./screens/python_screens.py'), here('./screens/scenarios.json')], {maxBuffer: 256 * 1024 * 1024, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore']}));

for (const [i, sc] of scenarios.entries()) {
  test(`screen scenario: ${sc.name}`, async () => {
    const {sqlite, env} = setup();
    const cookie = await signIn(env);
    for (const [j, s] of sc.steps.entries()) {
      const got = await step(env, cookie, s);
      const want = python[i].steps[j];
      if (typeof want.body === 'object' && typeof got.body === 'object' && got.body.body_html !== want.body.body_html && got.body.body_html && want.body.body_html) {
        // Show where the HTML first differs (the whole page is long).
        const a = got.body.body_html, b = want.body.body_html;
        let k = 0; while (k < a.length && a[k] === b[k]) k++;
        assert.fail(`step ${j} ${s.get || s.post}: body_html differs at ${k}\n  worker: ${JSON.stringify(a.slice(Math.max(0, k - 80), k + 120))}\n  python: ${JSON.stringify(b.slice(Math.max(0, k - 80), k + 120))}`);
      }
      assert.deepStrictEqual(got, want, `step ${j} ${s.get || s.post}`);
    }
    sqlite.close();
  });
}
test('scenarios ran on both servers', () => assert.equal(python.length, scenarios.length));
