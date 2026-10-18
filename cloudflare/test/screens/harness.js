// Shared by screens.test.js and cutover.test.js: an in-memory D1 with every
// migration and the test catalogue, and one request through the Worker.
import {DatabaseSync} from 'node:sqlite';
import {readFileSync, readdirSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import worker from '../../src/worker.js';
import {TOKEN} from '../../src/screens/index.js';
import {TERMS_VERSION} from '../../src/terms.js';

const here = p => new URL(p, import.meta.url).pathname;
const catalogue = JSON.parse(execFileSync('python3', [here('./catalogue.py'), '--sql'], {encoding: 'utf8', maxBuffer: 64 * 1024 * 1024}));
const ORIGIN = 'https://taguri.example';

export function setup() {
  const sqlite = new DatabaseSync(':memory:');
  for (const f of readdirSync(here('../../migrations/')).filter(n => n.endsWith('.sql')).sort()) sqlite.exec(readFileSync(here(`../../migrations/${f}`), 'utf8'));
  for (const stmt of catalogue.sql) sqlite.exec(stmt);
  let queue = Promise.resolve();
  const wrap = (sql, args = []) => ({bind(...v) { return wrap(sql, v); }, async first() { return sqlite.prepare(sql).get(...args) ?? null; }, async all() { return {results: sqlite.prepare(sql).all(...args)}; }, async run() { return sqlite.prepare(sql).run(...args); }, async execute() { return /^\s*SELECT/i.test(sql) ? this.all() : this.run(); }});
  const env = {ALLOW_REGISTRATION: 'true', ORIGINAL_UI_BRIDGE: 'true', NATIVE_UI: 'all', CLOCK: {today: catalogue.today, now: Date.parse(catalogue.today + 'T03:00:00Z')},
    // D1 は batch を 1 つずつ流す（同時に来た batch が 1 つのトランザクションの中で混ざらない）。ここでも順に並べる
    DB: {prepare: sql => wrap(sql), batch(cs) { const run = async () => { sqlite.exec('BEGIN'); try { const r = []; for (const c of cs) r.push(await c.execute()); sqlite.exec('COMMIT'); return r; } catch (e) { sqlite.exec('ROLLBACK'); throw e; } }; const p = queue.then(run); queue = p.catch(() => {}); return p; }},
    ASSETS: {fetch: () => new Response('')}};
  return {sqlite, env};
}
export async function signIn(env) {
  const res = await worker.fetch(new Request(`${ORIGIN}/migration-api/register`, {method: 'POST', headers: {origin: ORIGIN, 'content-type': 'application/json'}, body: JSON.stringify({agree: TERMS_VERSION})}), env);
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

