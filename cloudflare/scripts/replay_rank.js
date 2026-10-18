// 再生（tools/review/replay_eval.py replay）の橋。日 t までの記録だけに切った手元の SQLite で、
// Worker と同じ rankedGroups（screens/recommend.js）を利用者ごと・部品外しごとに動かし、
// 後で答えた公演がおすすめの何位だったかを返す。本番の D1 には触らない（無料枠を使わない）。
//
//   node cloudflare/scripts/replay_rank.js < job.json > ranks.json
//   job.json: {"db": "cut.sqlite", "today": "YYYY-MM-DD", "jobs": [{"uid", "variant", "ablate": {...}, "stages": [...]}]}
//
// 順位は表示の 1 枠ごと（ツアーの会場は同じ枠の順位）。残す 400 枠に入らない公演は null。
import {DatabaseSync} from 'node:sqlite';
import {rankedGroups} from '../src/screens/recommend.js';

/** node:sqlite を D1 の prepare / bind / first / all / run の形にする（test/screens/harness.js と同じ） */
export function d1Of(sqlite) {
  const wrap = (sql, args = []) => ({bind(...v) { return wrap(sql, v); }, async first() { return sqlite.prepare(sql).get(...args) ?? null; },
    async all() { return {results: sqlite.prepare(sql).all(...args)}; }, async run() { return sqlite.prepare(sql).run(...args); },
    async execute() { return /^\s*SELECT/i.test(sql) ? this.all() : this.run(); }});
  return {prepare: sql => wrap(sql), async batch(cs) { const r = []; for (const c of cs) r.push(await c.execute()); return r; }};
}

/** 枠ごとの順位（1 から）を、その枠の代表の公演と全部の会場に付ける */
export function ranksOf(groups, stages) {
  const at = new Map();
  groups.forEach((g, i) => {
    for (const s of [g.stage_id, ...(g.venues || []).map(v => v.stage_id)]) if (!at.has(String(s))) at.set(String(s), i + 1);
  });
  return Object.fromEntries(stages.map(s => [s, at.get(String(s)) ?? null]));
}

export async function run(job) {
  const sqlite = new DatabaseSync(job.db);
  try {
    const db = d1Of(sqlite), env = {DB: db};
    const now = Date.parse(job.today + 'T03:00:00Z');
    const out = [];
    for (const j of job.jobs) {
      const data = await rankedGroups({db, env, uid: j.uid, today: job.today, now, ablate: j.ablate || {}});
      out.push({uid: j.uid, variant: j.variant, n_rated: data.n_rated || 0, n_ranked: data.groups.length, ranks: ranksOf(data.groups, j.stages)});
    }
    return out;
  } finally {
    sqlite.close();
  }
}

if (import.meta.url === new URL(`file://${process.argv[1]}`).href) {
  const chunks = [];
  for await (const c of process.stdin) chunks.push(c);
  process.stdout.write(JSON.stringify(await run(JSON.parse(Buffer.concat(chunks).toString('utf8')))) + '\n');
}
