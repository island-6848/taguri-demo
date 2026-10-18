// 利用者ごとのセッションと同じ公演（tour）の会場をひく文が、0038 の索引を使うこと（issue #193）。
// 全 migration を当てた SQLite の EXPLAIN QUERY PLAN で見る。索引が無いと sessions は SCAN（全部の行）、
// rec_stage・rec_card は主キーの ver だけで SEARCH（その版の全部の行）になり、D1 の rows_read がその分増える。
// 文は Worker のものと同じ（下の SOURCES で、その文がいまもソースにあることも確かめる）。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync, readdirSync} from 'node:fs';

const sqlite = new DatabaseSync(':memory:');
for (const f of readdirSync(new URL('../migrations/', import.meta.url)).filter(n => /^\d{4}\.sql$/.test(n)).sort())
  sqlite.exec(readFileSync(new URL(`../migrations/${f}`, import.meta.url), 'utf8'));
const src = f => readFileSync(new URL(`../src/${f}`, import.meta.url), 'utf8');
const plan = (sql, ...args) => sqlite.prepare('EXPLAIN QUERY PLAN ' + sql).all(...args).map(r => r.detail).join(' | ');

const CASES = [
  {file: 'worker.js', index: 'sessions_user_expiry', args: ['u', 0, 'u'],
    sql: 'DELETE FROM sessions WHERE user_id=? AND (expires_at<=? OR hash NOT IN (SELECT hash FROM sessions WHERE user_id=? ORDER BY expires_at DESC LIMIT 9))'},
  {file: 'worker.js', index: 'sessions_user_expiry', args: ['u', 'h'], sql: 'DELETE FROM sessions WHERE user_id=? AND hash<>?'},
  {file: 'worker.js', index: 'sessions_user_expiry', args: ['u'], sql: 'DELETE FROM sessions WHERE user_id=?'},
  {file: 'screens/account.js', index: 'sessions_user_expiry', args: ['u', 0], sql: 'SELECT count(*) AS n FROM sessions WHERE user_id=? AND expires_at>?'},
  {file: 'screens/recommend.js', index: 'rec_stage_tour', args: ['live', 't1', 't2'],
    fragment: "FROM rec_stage WHERE ver=? AND tour IN (",
    sql: "SELECT stage_id,tour,start,end,json_extract(entry,'$.pref') AS pref FROM rec_stage WHERE ver=? AND tour IN (?,?)"},
  {file: 'screens/search.js', index: 'rec_stage_tour', args: ['t1', 't2'],
    fragment: "FROM rec_stage WHERE ver=(SELECT v FROM rec_meta WHERE k='current') AND tour IN (",
    sql: "SELECT stage_id, tour FROM rec_stage WHERE ver=(SELECT v FROM rec_meta WHERE k='current') AND tour IN (?,?)"},
  {file: 'screens/lists.js', index: 'rec_card_tour', args: ['t1', 't2'],
    fragment: "FROM rec_card WHERE ver=(SELECT v FROM rec_meta WHERE k='rec_card') AND tour IN (",
    sql: "SELECT stage_id,title,tour FROM rec_card WHERE ver=(SELECT v FROM rec_meta WHERE k='rec_card') AND tour IN (?,?)"},
  {file: 'screens/lists.js', index: 'rec_card_tour', args: ['t1'],
    fragment: "FROM rec_card WHERE ver=(SELECT v FROM rec_meta WHERE k='rec_card') AND tour=?",
    sql: "SELECT stage_id,title,tour FROM rec_card WHERE ver=(SELECT v FROM rec_meta WHERE k='rec_card') AND tour=?"},
];

for (const c of CASES) test(`${c.file}: ${c.sql.slice(0, 60)}… uses ${c.index}`, () => {
  assert.ok(src(c.file).includes(c.fragment || c.sql), `${c.file} にこの文が無い（変えたら CASES も直す）`);
  const p = plan(c.sql, ...c.args);
  assert.match(p, new RegExp(`USING (COVERING )?INDEX ${c.index}\\b`), p);
  assert.doesNotMatch(p, /\bSCAN (sessions|rec_stage|rec_card)\b/, p);
});

test('the daily sweep of empty accounts looks up sessions by user, not by scanning them', () => {
  // cleanup.js emptyAccount の sessions の部分（利用者ごとに 1 回ずつ走る相関副問い合わせ）
  assert.ok(src('cleanup.js').includes('NOT EXISTS (SELECT 1 FROM sessions s WHERE s.user_id=${u}.id'));
  const p = plan('SELECT id FROM users u WHERE u.created_at<?1 AND NOT EXISTS (SELECT 1 FROM sessions s WHERE s.user_id=u.id AND COALESCE(s.created_at, 0)>=?1) LIMIT 50', 0);
  assert.match(p, /SEARCH s USING INDEX sessions_user_expiry/, p);
});
