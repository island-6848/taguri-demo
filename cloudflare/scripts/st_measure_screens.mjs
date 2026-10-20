#!/usr/bin/env node
// システムテスト PF-01-02（docs/system-test-spec.md、S20）: おすすめ以外の主な画面が、Workers の無料枠の
// CPU 10 ミリ秒に収まるかを測る。measure_worker_replay.mjs はおすすめの計算だけを測る。これは Worker の
// 入口（worker.fetch）から /api/screen/<名前> を開き、画面ごとに測る。
//
//   node cloudflare/scripts/st_measure_screens.mjs --index d1-out/index.sql [--sizes 0,20,200] [--rep 9]
//   node cloudflare/scripts/st_measure_screens.mjs --fixture            # 手元の作り物の公演一覧で（形の確かめ）
//
// 測り方: 画面を開いたときのプロセスの CPU から、SQLite の中で使った CPU を引く（Workers では D1 を待つ間は
// CPU に数えない）。同じ人で 1 回開いてから（V8 の最初の組み立てと、推薦の作り置きを済ませてから）、
// --rep 回の真ん中の値といちばん遅い値を出す。返事の 1 回目の作り置き（rec_cache）は別に first_ms に出す。
// 測る機械は Workers と違うので、余裕を見て読む（手順書 P-06 の 8 ミリ秒の注意のライン）。
// 利用者の記録は使わない（作り物の利用者）。
import {DatabaseSync} from 'node:sqlite';
import {readFileSync, readdirSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {cpuUsage} from 'node:process';
const ROOT = new URL('..', import.meta.url).pathname.replace(/\/$/, '');
const {default: worker} = await import(ROOT + '/src/worker.js');
const {TERMS_VERSION} = await import(ROOT + '/src/terms.js');
const arg = (n, d) => { const i = process.argv.indexOf(n); return i > 0 ? process.argv[i + 1] : d; };
const SIZES = arg('--sizes', '0,20,200').split(',').map(Number), REP = +arg('--rep', 9);
const SCREENS = arg('--screens', 'rate,unrated,works,notes,calendar,search,account,interest,favourites,records,settings').split(',');

const sqlite = new DatabaseSync(':memory:');
for (const f of readdirSync(ROOT + '/migrations').filter(n => n.endsWith('.sql')).sort()) sqlite.exec(readFileSync(`${ROOT}/migrations/${f}`, 'utf8'));
let today = arg('--today', new Date(Date.now() + 9 * 3600e3).toISOString().slice(0, 10));
if (process.argv.includes('--fixture')) {
  const cat = JSON.parse(execFileSync('python3', [ROOT + '/test/screens/catalogue.py', '--sql'], {encoding: 'utf8', maxBuffer: 64 << 20}));
  for (const s of cat.sql) sqlite.exec(s);
  today = cat.today;
} else if (arg('--index')) sqlite.exec(readFileSync(arg('--index'), 'utf8'));
else { console.error('--index <索引の SQL> か --fixture を指定する'); process.exit(2); }

let inSql = 0;   // SQLite の中で使った CPU（マイクロ秒）
const timed = f => { const c0 = cpuUsage(); try { return f(); } finally { const c = cpuUsage(c0); inSql += c.user + c.system; } };
const wrap = (sql, args = []) => ({bind: (...v) => wrap(sql, v),
  first: async () => timed(() => sqlite.prepare(sql).get(...args) ?? null),
  all: async () => timed(() => ({results: sqlite.prepare(sql).all(...args)})),
  raw: async () => timed(() => sqlite.prepare(sql).all(...args).map(o => Object.values(o))),
  run: async () => timed(() => sqlite.prepare(sql).run(...args)),
  execute() { return /^\s*(SELECT|WITH)/i.test(sql) ? this.all() : this.run(); }});
const DB = {prepare: sql => wrap(sql), async batch(cs) { const r = []; timed(() => sqlite.exec('BEGIN')); try { for (const c of cs) r.push(await c.execute()); timed(() => sqlite.exec('COMMIT')); return r; } catch (e) { timed(() => sqlite.exec('ROLLBACK')); throw e; } }};
const env = {DB, ALLOW_REGISTRATION: 'true', ORIGINAL_UI_BRIDGE: 'false', NATIVE_UI: 'all', CLOCK: {today, now: Date.parse(today + 'T03:00:00Z')}, ASSETS: {fetch: () => new Response('')}};
const ORIGIN = 'https://taguri.example';
const stages = sqlite.prepare('SELECT id FROM catalogue').all().map(r => r.id);
let seed = 20261020;
const rand = () => { seed = (seed * 1103515245 + 12345) >>> 0; return seed / 2 ** 32; };
const med = xs => [...xs].sort((a, b) => a - b)[Math.floor(xs.length / 2)];

async function open(cookie, name) {
  inSql = 0; const c0 = cpuUsage();
  const res = await worker.fetch(new Request(`${ORIGIN}/api/screen/${name}`, {headers: {cookie}}), env);
  await res.arrayBuffer();
  const c = cpuUsage(c0);
  return {status: res.status, ms: (c.user + c.system - inSql) / 1000, sqlMs: inSql / 1000};
}

const out = [];
for (const n of SIZES) {
  const reg = await worker.fetch(new Request(`${ORIGIN}/migration-api/register`, {method: 'POST', headers: {origin: ORIGIN, 'content-type': 'application/json'}, body: JSON.stringify({agree: TERMS_VERSION})}), env);
  const cookie = reg.headers.get('set-cookie').split(';')[0];
  const uid = sqlite.prepare('SELECT id FROM users ORDER BY created_at DESC, rowid DESC LIMIT 1').get().id;
  const ins = sqlite.prepare("INSERT INTO works(user_id,work_key,title,first_date,last_date,times,verdict,stage_id,updated_at,rated_at,verdict_source) VALUES(?,?,?,?,?,1,?,?,?,?,'user')");
  for (let i = 0; i < n; i++) {
    const d = new Date(Date.UTC(2024, 0, 1) + Math.floor(rand() * 900) * 86400e3).toISOString().slice(0, 10);
    ins.run(uid, `m${i}`, `測る舞台 ${i}`, d, d, ['◎', '○', '△', '×'][Math.floor(rand() * 4)], stages.length && rand() < 0.6 ? stages[Math.floor(rand() * stages.length)] : null, `${d}T12:00:00`, `${d}T12:00:00`);
  }
  for (const name of SCREENS) {
    const first = await open(cookie, name);
    const runs = [];
    for (let r = 0; r < REP; r++) runs.push(await open(cookie, name));
    out.push({rated: n, screen: name, status: first.status, first_ms: +first.ms.toFixed(2), js_ms_median: +med(runs.map(r => r.ms)).toFixed(2), js_ms_max: +Math.max(...runs.map(r => r.ms)).toFixed(2), sql_ms_median: +med(runs.map(r => r.sqlMs)).toFixed(2), over_8ms: med(runs.map(r => r.ms)) > 8});
  }
}
console.log(JSON.stringify(out));
