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

// 記録を直す欄（<details class="editor">）は 2026-10-14 からサービス版（Worker）だけの形にした
// （起案者の指摘「公演詳細を編集するところがわかりにくい」「メール本文を見るってメールを保存してる？」）。
// Python は持ち主のメール機能つきのままなので、この欄だけは比べずに印に置き換え、形は drop-expiry.test.js で確かめる。
// 「いますぐ消す」（purge_work）もサービス版はその場で記録を消す（Python は印を付けるだけ）ので、比べずに drop-expiry.test.js で確かめる。
const EDITOR_PY = /<details class="editor"[\s\S]*?<div class="ed-mail" hidden>[\s\S]*?<\/div><\/details>/g;
const EDITOR_JS = /<details class="editor"[\s\S]*?<!--\/editor--><\/details>/g;
const noEditor = (r, re) => (r && typeof r.body === 'object' && typeof r.body?.body_html === 'string'
  ? {...r, body: {...r.body, body_html: r.body.body_html.replace(re, '<EDITOR/>')}} : r);

for (const [i, sc] of scenarios.entries()) {
  test(`screen scenario: ${sc.name}`, async () => {
    const {sqlite, env} = setup();
    const cookie = await signIn(env);
    for (const [j, s] of sc.steps.entries()) {
      const got = noEditor(await step(env, cookie, s), EDITOR_JS);
      const want = noEditor(python[i].steps[j], EDITOR_PY);
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
