#!/usr/bin/env node
// システムテスト PF-04-01・AV-05-03（docs/system-test-spec.md）: 手元の D1 に、作り物の利用者 N 人と、1 人 M 件の
// 観劇記録を入れる SQL を書き出す。本物の利用者の記録は使わない（利用者の id は st- で始まる）。
//
//   node scripts/st_seed_users.mjs --users 300 --records 200 --out /tmp/st-seed.sql [--stages ids.txt] [--seed 1]
//   npx wrangler d1 execute taguri-demo --local --persist-to "$ST_D1" --file /tmp/st-seed.sql
//
// --stages: 1 行に 1 つの公演の id（手元の D1 の catalogue から作る。手順書 P-05・P-06）。渡すと記録の
// 6 割を公演に結び付ける（推薦の計算に効く）。渡さなければ結び付けない。
// 評価は ◎ 2 割・○ 4 割・△ 2 割・× 1 割・未評価 1 割。同じ --seed なら毎回同じ SQL になる。
// 本番には流さない（--remote を付けない）。D1 の 1 日の書き込み 10 万行を、300 人 × 200 件で使い切る。
import {readFileSync, writeFileSync} from 'node:fs';

const arg = (name, dflt) => { const i = process.argv.indexOf(name); return i > 0 ? process.argv[i + 1] : dflt; };
const USERS = Number(arg('--users', 300)), RECORDS = Number(arg('--records', 200)), OUT = arg('--out');
if (!OUT || !(USERS > 0) || !(RECORDS >= 0) || RECORDS > 2000) { console.error('--out <file> を指定する（--records は 2000 まで: works の上限）'); process.exit(2); }
const stages = arg('--stages') ? readFileSync(arg('--stages'), 'utf8').split('\n').map(s => s.trim()).filter(Boolean) : [];

let state = Number(arg('--seed', 1)) >>> 0 || 1;
const rand = () => { state ^= state << 13; state >>>= 0; state ^= state >>> 17; state ^= state << 5; state >>>= 0; return state / 2 ** 32; };
const q = v => v === null ? 'NULL' : typeof v === 'number' ? String(v) : `'${String(v).replaceAll("'", "''")}'`;
const verdictOf = r => r < 0.2 ? '◎' : r < 0.6 ? '○' : r < 0.8 ? '△' : r < 0.9 ? '×' : null;
const day = n => new Date(Date.UTC(2024, 0, 1) + n * 86400e3).toISOString().slice(0, 10);

const lines = [];
const now = Date.now();
for (let u = 0; u < USERS; u++) {
  const id = `st-${String(u).padStart(4, '0')}`.padEnd(32, '0');
  lines.push(`INSERT INTO users (id, recovery_hash, created_at, terms_version, terms_at) VALUES (${q(id)}, ${q('st-not-a-real-hash-' + u)}, ${now - u * 60e3}, NULL, NULL);`);
  for (let k = 0; k < RECORDS; k++) {
    const date = day(Math.floor(rand() * 1000));
    const verdict = verdictOf(rand());
    const stage = stages.length && rand() < 0.6 ? stages[Math.floor(rand() * stages.length)] : null;
    lines.push(`INSERT INTO works (user_id, work_key, title, first_date, last_date, verdict, updated_at, stage_id, verdict_source, note_source, rated_at) VALUES (${[
      id, `st-${u}-${k}`, `試験の舞台 ${u}-${k}`, date, date, verdict, `${date}T12:00:00`, stage, verdict ? 'user' : 'legacy_unknown', 'legacy_unknown', verdict ? `${date}T12:00:00` : null,
    ].map(q).join(', ')});`);
  }
}
writeFileSync(OUT, lines.join('\n') + '\n');
console.log(JSON.stringify({users: USERS, records_per_user: RECORDS, rows: lines.length, linked_to_stages: stages.length > 0, out: OUT}));
