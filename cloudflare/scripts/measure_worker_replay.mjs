#!/usr/bin/env node
// 推薦（recommendFor）の JavaScript だけの CPU 時間を測る（#138）。measure_worker.mjs は SQLite の時間を
// 壁時計で引くので揺れが大きい（同じ索引で ±50%）。ここでは D1 の答えを 1 度記録し、2 回目からはその答えを
// JSON.parse で返す（D1 が結果を読み解くのと同じ形）ので、SQLite を通らず、Worker で数えられる CPU だけが残る。
//
//   node cloudflare/scripts/measure_worker_replay.mjs --index <索引の SQL> [--sizes 0,20,50] [--rep 15] [--today 2026-10-18] [--notes 0.5]
//
// --notes は感想を書いた記録の割合（#104 の感想の好み）。観た公演の種類の言葉（#題材など）を 1 つ選び、
// 半分は「〜が好きだった」、半分は「〜は苦手だった」と書く。
//
// 利用者の記録は使わない（作り物の利用者。measure_worker.mjs と同じ作り方・同じ種）。
import {DatabaseSync} from 'node:sqlite';
import {readFileSync, readdirSync} from 'node:fs';
import {cpuUsage} from 'node:process';
const ROOT = new URL('..', import.meta.url).pathname.replace(/\/$/, '');
const {recommendFor} = await import(ROOT + '/src/worker.js');
const arg = (n, d) => { const i = process.argv.indexOf(n); return i > 0 ? process.argv[i + 1] : d; };
const NOTES = +arg('--notes', 0), today = arg('--today', '2026-10-18'), SIZES = arg('--sizes', '0,5,20,50,100,300').split(',').map(Number), REP = +arg('--rep', 15);
const sqlite = new DatabaseSync(':memory:');
for (const f of readdirSync(ROOT + '/migrations').filter(n => n.endsWith('.sql')).sort()) sqlite.exec(readFileSync(`${ROOT}/migrations/${f}`, 'utf8'));
sqlite.exec(readFileSync(arg('--index'), 'utf8'));
let mode = 'rec', tape = [], pos = 0;
const exec = (kind, sql, args) => {
  if (mode === 'rec') {
    const st = sqlite.prepare(sql);
    const r = kind === 'first' ? (st.get(...args) ?? null) : kind === 'all' ? {results: st.all(...args)} : kind === 'raw' ? st.all(...args).map(o => Object.values(o)) : (st.run(...args), {});
    tape.push(JSON.stringify(r)); return r;
  }
  return JSON.parse(tape[pos++]);
};
const wrap = (sql, args = []) => ({bind: (...v) => wrap(sql, v), first: async () => exec('first', sql, args), all: async () => exec('all', sql, args), raw: async () => exec('raw', sql, args), run: async () => exec('run', sql, args)});
const db = {prepare: sql => wrap(sql)};
let seed = 20261014;
const rand = () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
const ver = sqlite.prepare("SELECT v FROM rec_meta WHERE k='current'").get().v;
const stages = sqlite.prepare('SELECT DISTINCT stage_id FROM rec_credit WHERE ver=?').all(ver).map(r => r.stage_id);
const persons = sqlite.prepare("SELECT person FROM rec_credit WHERE ver=? AND role NOT LIKE '#%' GROUP BY person ORDER BY count(*) DESC LIMIT 50").all(ver).map(r => r.person);
const groups = sqlite.prepare("SELECT grp FROM rec_stage WHERE ver=? AND grp<>'' GROUP BY grp ORDER BY count(*) DESC LIMIT 20").all(ver).map(r => r.grp);
const kindWords = new Map(sqlite.prepare('SELECT stage_id,people FROM rec_people WHERE ver=?').all(ver)
  .map(r => [r.stage_id, JSON.parse(r.people).filter(([role]) => role.startsWith('#') && role !== '#値段' && role !== '#会場').map(([, w]) => w)]));
const noteOf = sid => {
  const ws = kindWords.get(sid) || [];
  if (!ws.length || rand() >= NOTES) return '';
  const w = ws[Math.floor(rand() * ws.length)];
  return rand() < 0.5 ? `${w}の描写が好きだった。` : `${w}は苦手だった。`;
};
const med = xs => [...xs].sort((a, b) => a - b)[Math.floor(xs.length / 2)];
const res = [];
for (const n of [SIZES.at(-1), ...SIZES]) {
  const cpus = [];
  for (let k = 0; k < 5; k++) {
    const uid = `u-${n}-${k}-${res.length}`;
    sqlite.prepare('INSERT INTO users(id,recovery_hash,created_at) VALUES(?,?,0)').run(uid, uid);
    const ins = sqlite.prepare('INSERT INTO works(user_id,work_key,title,first_date,last_date,times,verdict,stage_id,updated_at,rated_at,note_impression) VALUES(?,?,?,?,?,1,?,?,?,?,?)');
    for (let i = 0; i < n; i++) { const at = `2025-01-01 00:${String(Math.floor(i / 60) % 60).padStart(2, '0')}:${String(i % 60).padStart(2, '0')}`; const sid = stages[Math.floor(rand() * stages.length)]; ins.run(uid, `r${i}`, 't', '2025-01-01', '2025-01-01', `${1 + Math.floor(rand() * 5)}/5`, sid, at, at, NOTES ? noteOf(sid) : ''); }
    const fav = sqlite.prepare('INSERT OR IGNORE INTO favourites(user_id,name,kind) VALUES(?,?,?)');
    fav.run(uid, persons[Math.floor(rand() * persons.length)], '人'); fav.run(uid, groups[Math.floor(rand() * groups.length)], '団体');
    mode = 'rec'; tape = []; await recommendFor(db, uid, today);
    for (let r = 0; r < REP; r++) { mode = 'play'; pos = 0; const c0 = cpuUsage(); await recommendFor(db, uid, today); const c = cpuUsage(c0); cpus.push((c.user + c.system) / 1000); }
  }
  res.push([n, +med(cpus).toFixed(2), +Math.max(...cpus).toFixed(2), tape.reduce((s, t) => s + t.length, 0)]);
}
res.shift();
console.log(JSON.stringify(res.map(([n, m, mx, bytes]) => ({rated: n, js_ms_median: m, js_ms_max: mx, d1_json_bytes_last: bytes}))));
