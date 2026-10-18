// 件数の上限のトリガーは、増える書き込みだけを止める（issue #188、migrations/0037）。
// 前は ticket・reaction・missed のトリガーが総数だけを見ていたので、上限に届いた人は、
// 既にある行の付け直し（INSERT ... ON CONFLICT DO UPDATE。BEFORE INSERT が先に動く）まで断られた。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {setup} from './screens/harness.js';

const T = '2026-10-18T00:00:00';
// 表 → [上限, i 番目の行を入れる文, 既にある行を付け直す文, 新しい行を入れる文]
const CASES = {
  ticket: [2000,
    i => [`INSERT INTO ticket(user_id,stage_id,date,time,source,updated_at) VALUES('u',?, '2026-11-01','',?,?)`, [String(i), 'screen', T]],
    [`INSERT INTO ticket(user_id,stage_id,date,time,source,confirmed,updated_at) VALUES('u','0','2026-11-01','','screen',1,?)
      ON CONFLICT(user_id,stage_id,date,time) DO UPDATE SET confirmed=excluded.confirmed`, [T]],
    [`INSERT INTO ticket(user_id,stage_id,date,time,source,updated_at) VALUES('u','new','2026-11-01','','screen',?)`, [T]]],
  reaction: [5000,
    i => [`INSERT INTO reaction(user_id,label,stage_id,interest,source,updated_at) VALUES('u','2026-10-18',?,1,?,?)`, [String(i), 'screen', T]],
    [`INSERT INTO reaction(user_id,label,stage_id,interest,source,updated_at) VALUES('u','2026-10-18','0',0,'screen',?)
      ON CONFLICT(user_id,label,stage_id) DO UPDATE SET interest=excluded.interest`, [T]],
    [`INSERT INTO reaction(user_id,label,stage_id,interest,source,updated_at) VALUES('u','2026-10-18','new',1,'screen',?)`, [T]]],
  missed: [500,
    i => [`INSERT INTO missed(user_id,title,created_at) VALUES('u',?,?)`, [`題${i}`, T]],
    [`INSERT INTO missed(user_id,title,created_at,note) VALUES('u','題0',?,'メモ')
      ON CONFLICT(user_id,title) DO UPDATE SET note=excluded.note`, [T]],
    [`INSERT INTO missed(user_id,title,created_at) VALUES('u','新しい題',?)`, [T]]],
};

for (const [table, [limit, row, upsert, fresh]] of Object.entries(CASES)) {
  test(`${table}: at the limit an existing row can still be upserted, a new one is refused`, () => {
    const {sqlite} = setup();
    try {
      sqlite.prepare("INSERT INTO users(id,recovery_hash,created_at) VALUES('u','h',0)").run();
      sqlite.exec('BEGIN');
      for (let i = 0; i < limit; i++) { const [s, a] = row(i); sqlite.prepare(s).run(...a); }
      sqlite.exec('COMMIT');
      sqlite.prepare(upsert[0]).run(...upsert[1]);
      assert.throws(() => sqlite.prepare(fresh[0]).run(...fresh[1]), new RegExp(`${table} limit`));
      assert.equal(sqlite.prepare(`SELECT count(*) n FROM ${table} WHERE user_id='u'`).get().n, limit);
    } finally { sqlite.close(); }
  });
}

test('every BEFORE INSERT limit trigger on a per-user table skips rows whose key already exists', () => {
  const {sqlite} = setup();
  try {
    const triggers = sqlite.prepare("SELECT name, tbl_name, sql FROM sqlite_master WHERE type='trigger' AND sql LIKE '%limit%' AND sql LIKE '%BEFORE INSERT%'").all();
    assert.ok(triggers.length >= 10);
    // アカウントの数（users）とパスキー（追加だけで、付け直しが無い）は総数で止めてよい
    for (const t of triggers.filter(t => !['users', 'passkeys'].includes(t.tbl_name))) {
      assert.match(t.sql, /WHEN\s+NOT\s+EXISTS/i, t.name);
    }
  } finally { sqlite.close(); }
});
