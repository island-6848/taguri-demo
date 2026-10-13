// The original screens ported to the Worker (src/screens/) must answer exactly
// as the Python app on Render does. test/screens/python_screens.py runs each
// scenario in test/screens/scenarios.json on the Python app; here the same
// steps run on the Worker (NATIVE_UI=all) with a fresh signed-in account.
import {DatabaseSync} from 'node:sqlite';
import {readFileSync, readdirSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import worker from '../src/worker.js';
import {TOKEN} from '../src/screens/index.js';

const here = p => new URL(p, import.meta.url).pathname;
const scenarios = JSON.parse(readFileSync(here('./screens/scenarios.json'), 'utf8'));
const python = JSON.parse(execFileSync('python3', [here('./screens/python_screens.py'), here('./screens/scenarios.json')], {maxBuffer: 256 * 1024 * 1024, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore']}));
const catalogue = JSON.parse(execFileSync('python3', [here('./screens/catalogue.py'), '--sql'], {encoding: 'utf8', maxBuffer: 64 * 1024 * 1024}));
const ORIGIN = 'https://taguri.example';

export function setup() {
  const sqlite = new DatabaseSync(':memory:');
  for (const f of readdirSync(here('../migrations/')).filter(n => n.endsWith('.sql')).sort()) sqlite.exec(readFileSync(here(`../migrations/${f}`), 'utf8'));
  for (const stmt of catalogue.sql) sqlite.exec(stmt);
  const wrap = (sql, args = []) => ({bind(...v) { return wrap(sql, v); }, async first() { return sqlite.prepare(sql).get(...args) ?? null; }, async all() { return {results: sqlite.prepare(sql).all(...args)}; }, async run() { return sqlite.prepare(sql).run(...args); }, async execute() { return /^\s*SELECT/i.test(sql) ? this.all() : this.run(); }});
  const env = {ALLOW_REGISTRATION: 'true', ORIGINAL_UI_BRIDGE: 'true', NATIVE_UI: 'all', CLOCK: {today: catalogue.today, now: Date.parse(catalogue.today + 'T03:00:00Z')},
    DB: {prepare: sql => wrap(sql), async batch(cs) { sqlite.exec('BEGIN'); try { const r = []; for (const c of cs) r.push(await c.execute()); sqlite.exec('COMMIT'); return r; } catch (e) { sqlite.exec('ROLLBACK'); throw e; } }},
    ASSETS: {fetch: () => new Response('')}};
  return {sqlite, env};
}
async function signIn(env) {
  const res = await worker.fetch(new Request(`${ORIGIN}/migration-api/register`, {method: 'POST', headers: {origin: ORIGIN, 'content-type': 'application/json'}, body: '{}'}), env);
  return res.headers.get('set-cookie').split(';')[0];
}
export async function step(env, cookie, s) {
  const path = s.get || s.post;
  const init = s.post ? {method: 'POST', headers: {cookie, origin: ORIGIN, 'content-type': 'application/json'}, body: JSON.stringify(s.body)} : {headers: {cookie}};
  const res = await worker.fetch(new Request(ORIGIN + path, init), env);
  const text = await res.text();
  let body;
  try { body = JSON.parse(text.replaceAll(TOKEN, '__TAGURI_TOKEN__')); } catch { body = text; }
  return {status: res.status, body};
}

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
