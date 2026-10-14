#!/usr/bin/env node
// How much CPU and how many D1 rows the Worker's recommendation takes on the
// real index (S20・S21, q-workers-cpu-real・q-real-catalog-stats).
//
//   node cloudflare/scripts/measure_worker.mjs --index d1-out/index.sql [--today 2026-10-15]
//
// Run where the real index is built (the crawler's daily job): this machine
// cannot reach the catalogue. The index SQL is loaded into an in-memory SQLite
// with every migration; made-up users with 0 to 300 rated stages (stages drawn
// from the index, at random, fixed seed) and a few favourites then get their
// recommendations computed exactly as the Worker does (recommendFor, cache off).
//
// What it reports per history size: the JavaScript CPU time with the time spent
// inside SQLite taken out (on Workers, waiting for D1 is not CPU time), the
// SQLite time separately, and the rows read. Workers Free allows 10 ms of CPU
// per request; V8 here is the same engine, but a different machine, so read
// the numbers with a margin (the limit is checked against the median of 9, after
// one warm-up user so V8's first compile is not counted; the slowest run is shown too).
// No user data is involved: only the public catalogue's index.
import {DatabaseSync} from 'node:sqlite';
import {readFileSync, readdirSync} from 'node:fs';
import {cpuUsage} from 'node:process';
import {recommendFor} from '../src/worker.js';

const arg = (name, dflt) => { const i = process.argv.indexOf(name); return i > 0 ? process.argv[i + 1] : dflt; };
const indexPath = arg('--index');
if (!indexPath) { console.error('--index <index.sql> を指定する'); process.exit(2); }
const today = arg('--today', new Date(Date.now() + 9 * 3600e3).toISOString().slice(0, 10));
const SIZES = (arg('--sizes', '0,5,20,50,100,300')).split(',').map(Number);
const REPEAT = 9;
const LIMIT_MS = 10;

const sqlite = new DatabaseSync(':memory:');
for (const f of readdirSync(new URL('../migrations/', import.meta.url)).filter(n => n.endsWith('.sql')).sort())
  sqlite.exec(readFileSync(new URL(`../migrations/${f}`, import.meta.url), 'utf8'));
sqlite.exec(readFileSync(indexPath, 'utf8'));

// D1 stand-in that counts rows and the time spent inside SQLite.
const meter = {sqlMs: 0, rows: 0};
const timed = (fn, rowsOf) => { const t = performance.now(); const r = fn(); meter.sqlMs += performance.now() - t; meter.rows += rowsOf(r); return r; };
const wrap = (sql, args = []) => ({
  bind(...v) { return wrap(sql, v); },
  async first() { return timed(() => sqlite.prepare(sql).get(...args) ?? null, r => (r ? 1 : 0)); },
  async all() { return {results: timed(() => sqlite.prepare(sql).all(...args), r => r.length)}; },
  async run() { return timed(() => sqlite.prepare(sql).run(...args), () => 0); },
});
const db = {prepare: sql => wrap(sql)};

// Fixed-seed random numbers (mulberry32) so runs are comparable day to day.
let seed = 20261014;
const rand = () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
const ver = sqlite.prepare("SELECT v FROM rec_meta WHERE k='current'").get()?.v;
if (!ver) { console.error('索引に rec_meta current が無い'); process.exit(2); }
const stages = sqlite.prepare('SELECT DISTINCT stage_id FROM rec_credit WHERE ver=?').all(ver).map(r => r.stage_id);
const persons = sqlite.prepare("SELECT person FROM rec_credit WHERE ver=? AND role NOT LIKE '#%' GROUP BY person ORDER BY count(*) DESC LIMIT 50").all(ver).map(r => r.person);
const groups = sqlite.prepare("SELECT grp FROM rec_stage WHERE ver=? AND grp<>'' GROUP BY grp ORDER BY count(*) DESC LIMIT 20").all(ver).map(r => r.grp);

const median = xs => [...xs].sort((a, b) => a - b)[Math.floor(xs.length / 2)];
const out = {today, index: {version: ver, stages: stages.length,
  credits: sqlite.prepare('SELECT count(*) AS n FROM rec_credit WHERE ver=?').get(ver).n,
  people: sqlite.prepare('SELECT count(*) AS n FROM rec_people WHERE ver=?').get(ver).n,
  upcoming: sqlite.prepare('SELECT count(*) AS n FROM rec_stage WHERE ver=? AND end>=?').get(ver, today).n},
  limit_ms: LIMIT_MS, sizes: []};
for (const n of [SIZES[SIZES.length - 1], ...SIZES]) {
  const warm = out.sizes.length === 0 && !out.warmed;
  const runs = [];
  for (let k = 0; k < (warm ? 1 : REPEAT); k++) {
    const uid = `measure-${warm ? 'w' : n}-${k}`;
    sqlite.prepare('INSERT INTO users(id,recovery_hash,created_at) VALUES(?,?,0)').run(uid, uid);
    const ins = sqlite.prepare('INSERT INTO records(user_id,id,title,date,rating,stage_id,updated_at) VALUES(?,?,?,?,?,?,?)');
    for (let i = 0; i < n; i++)
      ins.run(uid, `r${i}`, 't', '2025-01-01', `${1 + Math.floor(rand() * 5)}/5`, stages[Math.floor(rand() * stages.length)], i);
    const fav = sqlite.prepare('INSERT OR IGNORE INTO favourites(user_id,name,kind) VALUES(?,?,?)');
    if (persons.length) fav.run(uid, persons[Math.floor(rand() * persons.length)], '人');
    if (groups.length) fav.run(uid, groups[Math.floor(rand() * groups.length)], '団体');
    Object.assign(meter, {sqlMs: 0, rows: 0});
    const c0 = cpuUsage();
    const body = await recommendFor(db, uid, today);
    const c = cpuUsage(c0), cpuMs = (c.user + c.system) / 1000;
    runs.push({cpu: cpuMs, sql: meter.sqlMs, js: Math.max(0, cpuMs - meter.sqlMs), rows: meter.rows, items: body.items.length, seeds: body.n_seeds});
  }
  if (warm) { out.warmed = true; continue; }
  const js = median(runs.map(r => r.js));
  out.sizes.push({rated: n, js_cpu_ms: +js.toFixed(2), sqlite_ms: +median(runs.map(r => r.sql)).toFixed(2),
    js_cpu_ms_max: +Math.max(...runs.map(r => r.js)).toFixed(2), rows_read: median(runs.map(r => r.rows)), items: median(runs.map(r => r.items)), within_limit: js <= LIMIT_MS});
}
delete out.warmed;
out.ok = out.sizes.every(s => s.within_limit);
console.log(JSON.stringify(out));
process.exit(0);
