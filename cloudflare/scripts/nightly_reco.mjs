#!/usr/bin/env node
// おすすめを全員分、前もって作る（起案者の決定 2026-10-24「おすすめの計算し直しは A で進めて」、dec-reco-nightly）。
//
//   CLOUDFLARE_API_TOKEN=… CLOUDFLARE_ACCOUNT_ID=… node cloudflare/scripts/nightly_reco.mjs [--today YYYY-MM-DD] [--dry-run]
//
// なぜ: 本番の大きさでは、おすすめの計算し直しが評価 10 件で 17 ms・40 件で 37 ms あり、Workers Free の CPU 10 ms を
// 越えて Cloudflare に止められていた（f-reco-recompute-cpu-1021）。Worker は控え（rec_cache）が古くても計算し直さず、
// 答えた公演だけを外して出す（screens/recommend.js の staleGroups）。計算はここで、取得の夜の段（taguri-crawler の
// Catalog、索引を D1 に入れたあと）に Worker と同じコード（rankedGroups）で行う。
//
// - 読むのは、おすすめの計算が読む表だけ（TABLES）。D1 の REST API の SELECT で、番号（rowid）順に区切って読む。
//   D1 の export は使わない（書き出しのあいだ D1 が答えなくなる。公式の API の説明）
// - 利用者の記録は、この機械のメモリの中の SQLite にだけ置く。ファイル・ログ・作業データ（state ブランチ）には書かない。
//   ログに出すのは件数だけ
// - 書き戻すのは、印（stamp）か中身が変わった人の rec_cache の 1 行だけ。D1 の文の長さの上限（100 KB）を越えないよう、
//   中身は SQL の文に埋めずに引数（params）で送る。読んでから書くまでのあいだに Worker が作り直した控え（登録した直後の
//   人など）は上書きしない（created_at が読み始めより後なら飛ばす）
// - 無料枠: 読む行は 1 日 10 万行ほど（D1 の無料は 1 日 500 万行）。MAX_ROWS_READ を越えそうなら途中でやめる。
//   書くのは多くて利用者の数（上限 300 人）
import {DatabaseSync} from 'node:sqlite';
import {readFileSync, readdirSync} from 'node:fs';
import {rankedGroups} from '../src/screens/recommend.js';

// おすすめの計算（rankedGroups とその下）が読む表。試験（test/nightly-reco.test.js）で、ここに無い表を読んでいないかを確かめる
export const TABLES = ['users', 'works', 'work_piece', 'reaction', 'favourites', 'excluded', 'merges', 'app_setting', 'rank_weight',
  'hand_credits', 'note_ai', 'ticket', 'venue_pref', 'stage_override', 'rec_meta', 'rec_stage', 'rec_credit', 'rec_people', 'rec_affil',
  'catalogue', 'past_stage', 'stage_label', 'rec_cache'];
const PAGE = 2000;
export const MAX_ROWS_READ = 400_000;      // 1 日の無料 500 万行の 8%。越えるなら何かがおかしいので、書き戻さずにやめる

const here = p => new URL(p, import.meta.url);

/** 手元の SQLite を、D1 の db と同じ呼び方（prepare・bind・first・all・run・batch）で包む */
export function d1Shim(sqlite) {
  const wrap = (sql, args = []) => ({bind(...v) { return wrap(sql, v); }, async first() { return sqlite.prepare(sql).get(...args) ?? null; },
    async all() { return {results: sqlite.prepare(sql).all(...args)}; }, async run() { return sqlite.prepare(sql).run(...args); }});
  return {prepare: sql => wrap(sql), async batch(cs) { const r = []; for (const c of cs) r.push(await c.run()); return r; }};
}

/** 本番の D1 に REST API で 1 文送る（引数つき）。答えは {results, rows_read} */
export function d1Rest({account, token, database}) {
  return async (sql, params = []) => {
    const res = await fetch(`https://api.cloudflare.com/client/v4/accounts/${account}/d1/database/${database}/query`, {
      method: 'POST', headers: {authorization: `Bearer ${token}`, 'content-type': 'application/json'}, body: JSON.stringify({sql, params})});
    const j = await res.json().catch(() => ({}));
    // 失敗の説明は出すが、文や値（利用者の記録）は出さない
    if (!res.ok || !j.success) throw new Error(`D1 の問い合わせが失敗した（${res.status}）: ${(j.errors || []).map(e => e.message).join(' / ').slice(0, 200)}`);
    const r = j.result?.[0] || {};
    return {results: r.results || [], rows_read: r.meta?.rows_read ?? 0};
  };
}

/** 手元に、全部の migration と、本番の TABLES の行を写す。トリガーは外す（写すときに rec_rev が進むと印が本番と違ってしまう） */
export async function copyTables(query, {maxRowsRead = MAX_ROWS_READ} = {}) {
  const sqlite = new DatabaseSync(':memory:', {enableForeignKeyConstraints: false});
  for (const f of readdirSync(here('../migrations/')).filter(n => n.endsWith('.sql')).sort()) sqlite.exec(readFileSync(here(`../migrations/${f}`), 'utf8'));
  for (const {name} of sqlite.prepare("SELECT name FROM sqlite_master WHERE type='trigger'").all()) sqlite.exec(`DROP TRIGGER "${name}"`);
  const counts = {};
  let rowsRead = 0;
  for (const t of TABLES) {
    counts[t] = 0;
    let after = -1;
    for (;;) {
      const {results, rows_read} = await query(`SELECT rowid AS _rowid_, * FROM "${t}" WHERE rowid > ? ORDER BY rowid LIMIT ${PAGE}`, [after]);
      rowsRead += rows_read || results.length;
      if (rowsRead > maxRowsRead) throw new Error(`D1 から読む行が ${maxRowsRead} を越えるのでやめる（無料枠を守る）`);
      if (!results.length) break;
      const cols = Object.keys(results[0]).filter(c => c !== '_rowid_');
      const ins = sqlite.prepare(`INSERT INTO "${t}"(rowid, ${cols.map(c => `"${c}"`).join(',')}) VALUES (?, ${cols.map(() => '?').join(',')})`);
      sqlite.exec('BEGIN');
      for (const r of results) ins.run(r._rowid_, ...cols.map(c => r[c]));
      sqlite.exec('COMMIT');
      counts[t] += results.length;
      after = results[results.length - 1]._rowid_;
      if (results.length < PAGE) break;
    }
  }
  return {sqlite, counts, rowsRead};
}

/** 全員分を計算し、変わった控えを書き戻す。query は D1 への 1 文（本番は d1Rest、試験は手元の SQLite） */
export async function run(query, {today, now, dryRun = false, log = () => {}} = {}) {
  const started = Math.floor(now / 1000);
  const {sqlite, counts, rowsRead} = await copyTables(query);
  try {
    const before = new Map(sqlite.prepare('SELECT user_id, stamp, body FROM rec_cache').all().map(r => [r.user_id, r]));
    const db = d1Shim(sqlite);
    const users = sqlite.prepare('SELECT id FROM users ORDER BY id').all().map(r => r.id);
    const out = {users: users.length, rows_read: rowsRead, tables: counts, computed: 0, failed: 0, changed: 0, written: 0, skipped: 0, ms: 0};
    const t0 = performance.now();
    const changed = [];
    for (const uid of users) {
      try {
        await rankedGroups({db, env: {}, uid, today, now, recompute: true});
        out.computed += 1;
      } catch (e) {
        out.failed += 1;            // 誰の計算が落ちたかは書かない（番号も利用者の記録の一部）
        log(`計算に失敗: ${String(e?.message || e).slice(0, 120)}`);
        continue;
      }
      const row = sqlite.prepare('SELECT stamp, body, created_at FROM rec_cache WHERE user_id=?').get(uid);
      const old = before.get(uid);
      if (row && (!old || old.stamp !== row.stamp || old.body !== row.body)) changed.push([uid, row]);
    }
    out.ms = Math.round(performance.now() - t0);
    out.changed = changed.length;
    if (dryRun) return out;
    for (const [uid, row] of changed) {
      // 読み始めより後に Worker が作り直した控えは上書きしない（その人の最新の計算なので）
      const r = await query(`INSERT INTO rec_cache(user_id,stamp,body,created_at) VALUES(?1,?2,?3,?4)
        ON CONFLICT(user_id) DO UPDATE SET stamp=excluded.stamp, body=excluded.body, created_at=excluded.created_at
        WHERE rec_cache.created_at < ?5 RETURNING user_id`, [uid, row.stamp, row.body, row.created_at, started]).catch(e => {
        log(`書き戻しに失敗: ${String(e?.message || e).slice(0, 120)}`);
        return null;
      });
      if (r?.results?.length) out.written += 1; else out.skipped += 1;
    }
    return out;
  } finally { sqlite.close(); }
}

async function main() {
  const arg = (name, dflt) => { const i = process.argv.indexOf(name); return i > 0 ? process.argv[i + 1] : dflt; };
  const account = process.env.CLOUDFLARE_ACCOUNT_ID, token = process.env.CLOUDFLARE_API_TOKEN;
  if (!account || !token) { console.log('CLOUDFLARE_API_TOKEN・CLOUDFLARE_ACCOUNT_ID が無いので、おすすめの前もっての計算はしない'); return; }
  const database = /"database_id"\s*:\s*"([^"]+)"/.exec(readFileSync(here('../wrangler.jsonc'), 'utf8'))?.[1];
  const now = Date.now();
  const today = arg('--today', new Date(now + 9 * 3600e3).toISOString().slice(0, 10));
  const out = await run(d1Rest({account, token, database}), {today, now, dryRun: process.argv.includes('--dry-run'), log: m => console.log(m)});
  console.log(JSON.stringify(out));
  if (out.failed) process.exitCode = 1;
}

if (import.meta.url === `file://${process.argv[1]}`) await main();
