import {SESSION_TTL} from '../src/session-policy.js';
// 記録の無いアカウントを 1 か月で片付ける（src/cleanup.js、起案者の指示 2026-10-18「1ヶ月で消してほしい」）。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync, readdirSync} from 'node:fs';
import {sweepEmptyAccounts, EMPTY_ACCOUNT_DAYS, ACCOUNT_TABLES, RECORD_TABLES} from '../src/cleanup.js';
import worker from '../src/worker.js';

function db() {
  const sqlite = new DatabaseSync(':memory:');
  for (const f of readdirSync(new URL('../migrations/', import.meta.url)).filter(n => n.endsWith('.sql')).sort()) sqlite.exec(readFileSync(new URL(`../migrations/${f}`, import.meta.url), 'utf8'));
  const wrap = (sql, args = []) => ({bind(...v) { return wrap(sql, v); }, async first() { return sqlite.prepare(sql).get(...args) ?? null; }, async all() { return {results: sqlite.prepare(sql).all(...args)}; }, async run() { return sqlite.prepare(sql).run(...args); }});
  return {sqlite, d1: {prepare: sql => wrap(sql), async batch(cs) { sqlite.exec('BEGIN'); try { const r = []; for (const c of cs) r.push(await c.run()); sqlite.exec('COMMIT'); return r; } catch (e) { sqlite.exec('ROLLBACK'); throw e; } }}};
}
const NOW = 1_800_000_000, DAY = 86400;
const user = (sqlite, id, ageDays) => sqlite.prepare('INSERT INTO users(id,recovery_hash,created_at) VALUES(?,?,?)').run(id, 'h-' + id, NOW - ageDays * DAY);

test('an account with no records, older than a month and not signed in for a month, is removed; others stay', async () => {
  const {sqlite, d1} = db();
  user(sqlite, 'old-empty', EMPTY_ACCOUNT_DAYS + 1);
  user(sqlite, 'new-empty', EMPTY_ACCOUNT_DAYS - 1);
  user(sqlite, 'old-with-work', 90);
  user(sqlite, 'old-with-fav', 90);
  user(sqlite, 'old-signed-in', 90);
  sqlite.prepare("INSERT INTO works(user_id,work_key,title,updated_at) VALUES('old-with-work','k','題','2026-01-01 00:00:00')").run();
  sqlite.prepare("INSERT INTO favourites(user_id,name,kind) VALUES('old-with-fav','名前','人')").run();
  sqlite.prepare('INSERT INTO sessions(hash,user_id,expires_at,created_at) VALUES(?,?,?,?)').run('s1', 'old-signed-in', NOW + DAY, NOW - 2 * DAY);
  // 設定・控えだけ、古いセッションだけのアカウントは、記録が無いので消える
  sqlite.prepare("INSERT INTO app_setting(user_id,key,value,updated_at) VALUES('old-empty','scale','star','x')").run();
  sqlite.prepare('INSERT INTO sessions(hash,user_id,expires_at,created_at) VALUES(?,?,?,?)').run('s0', 'old-empty', NOW - 40 * DAY, NOW - 70 * DAY);
  assert.equal(await sweepEmptyAccounts(d1, NOW), 1);
  const left = sqlite.prepare('SELECT id FROM users ORDER BY id').all().map(r => r.id);
  assert.deepEqual(left, ['new-empty', 'old-signed-in', 'old-with-fav', 'old-with-work']);
  for (const t of ACCOUNT_TABLES) assert.equal(sqlite.prepare(`SELECT count(*) AS n FROM ${t} WHERE user_id='old-empty'`).get().n, 0, t);
  assert.equal(await sweepEmptyAccounts(d1, NOW), 0);          // 2 回目は何もしない
});

test('the Worker has the daily scheduled handler and the cron', () => {
  assert.equal(typeof worker.scheduled, 'function');
  assert.match(readFileSync(new URL('../wrangler.jsonc', import.meta.url), 'utf8'), /"triggers":\s*\{\s*"crons":\s*\["[^"]+"\]/);
});

// ---- issue #137: 定期実行の片付けが、本人の記録のあるアカウントを消さないこと ----

// 利用者の行を持つ表（user_id の列がある表）のうち、記録に数えない表と、その理由。
// 新しい表を足したら、RECORD_TABLES（記録に数える）かここ（数えない）のどちらかに入れないと落ちる
const NOT_RECORDS = {
  app_setting: '設定（privacy.html 第 6 条: 設定だけを変えたアカウントも消す）',
  rank_weight: '推薦の効かせ方の設定（設定と同じ扱い）',
  viewed: '画面を見た控え（旧版の分析用）',
  rec_cache: 'おすすめの作り置き',
  rec_shown: '出した公演の控え（測るため）',
  sessions: 'ログイン（30 日以内のログインは別の条件で守る）',
  passkeys: 'ログインの手段',
  webauthn_challenges: 'ログインの途中',
  fix_request: '公演修正依頼（消すときはトリガーで本文と利用者だけ外す）',
  share: '共有リンク（記録の見せ方の設定。記録が無ければ見せるものも無い）',
  note_ai: '感想を AI で読み取った結果（感想から作り直せる。感想が無ければ行も無い）',
};
const userTables = sqlite => sqlite.prepare("SELECT name FROM sqlite_master WHERE type='table'").all().map(r => r.name)
  .filter(t => sqlite.prepare(`PRAGMA table_info(${t})`).all().some(c => c.name === 'user_id')).sort();

test('every table holding user rows is either counted as a record or listed with the reason it is not', () => {
  const {sqlite} = db();
  const tables = userTables(sqlite);
  for (const t of tables) assert.ok(RECORD_TABLES.includes(t) !== (t in NOT_RECORDS), `${t}: RECORD_TABLES か NOT_RECORDS のどちらか一方に入れる`);
  for (const t of [...RECORD_TABLES, ...Object.keys(NOT_RECORDS)]) assert.ok(tables.includes(t), `${t} は無い表`);
  // アカウントを消すとき、利用者の行を持つ表はすべて消す（fix_request はトリガーで利用者と本文を外す）
  for (const t of tables) assert.ok(ACCOUNT_TABLES.includes(t) || t === 'fix_request', `${t} がアカウントの削除で残る`);
});

/** 表の列に入れる値（1 行。CHECK のある列だけ決まった値） */
function rowFor(sqlite, table, uid, i = 0) {
  const fixed = {user_id: uid, status: 'interest', purpose: 'login', kind: '人', name: '名前' + i};
  const cols = sqlite.prepare(`PRAGMA table_info(${table})`).all().filter(c => !(c.pk && c.type === 'INTEGER' && table === 'fix_request'));
  const vals = cols.map(c => c.name in fixed ? fixed[c.name] : /INT/i.test(c.type) ? i + 1 : /REAL/i.test(c.type) ? 0.5 : `${table}.${c.name}.${i}`);
  sqlite.prepare(`INSERT INTO ${table}(${cols.map(c => c.name).join(',')}) VALUES(${cols.map(() => '?').join(',')})`).run(...vals);
}

test('an old, signed-out account with a single row in any record table is kept', async () => {
  for (const t of RECORD_TABLES) {
    const {sqlite, d1} = db();
    user(sqlite, 'u', 90);
    rowFor(sqlite, t, 'u');
    assert.equal(await sweepEmptyAccounts(d1, NOW), 0, t);
    assert.equal(sqlite.prepare("SELECT count(*) AS n FROM users WHERE id='u'").get().n, 1, t);
    assert.equal(sqlite.prepare(`SELECT count(*) AS n FROM ${t} WHERE user_id='u'`).get().n, 1, t);
  }
});

test('an account with only settings, a passkey or old caches goes (privacy.html article 6), and takes only its own rows', async () => {
  const {sqlite, d1} = db();
  user(sqlite, 'settings-only', 90);
  user(sqlite, 'neighbour', 90);
  for (const t of Object.keys(NOT_RECORDS).filter(t => t !== 'sessions')) rowFor(sqlite, t, 'settings-only');
  for (const t of RECORD_TABLES) rowFor(sqlite, t, 'neighbour');
  for (const t of Object.keys(NOT_RECORDS).filter(t => t !== 'sessions')) rowFor(sqlite, t, 'neighbour', 1);
  const before = Object.fromEntries(userTables(sqlite).map(t => [t, sqlite.prepare(`SELECT * FROM ${t} WHERE user_id='neighbour'`).all()]));
  assert.equal(await sweepEmptyAccounts(d1, NOW), 1);
  assert.deepEqual(sqlite.prepare('SELECT id FROM users').all().map(r => r.id), ['neighbour']);
  for (const t of ACCOUNT_TABLES) assert.equal(sqlite.prepare(`SELECT count(*) AS n FROM ${t} WHERE user_id='settings-only'`).get().n, 0, t);
  // 公演修正依頼は対応の記録として残し、送った人と本文だけ外す（0030 のトリガー）
  assert.deepEqual(sqlite.prepare("SELECT user_id, message FROM fix_request WHERE id<>(SELECT id FROM fix_request WHERE user_id='neighbour')").all().map(r => ({...r})),
    [{user_id: '', message: '（アカウント削除により消去）'}]);
  for (const [t, rows] of Object.entries(before)) assert.deepEqual(sqlite.prepare(`SELECT * FROM ${t} WHERE user_id='neighbour'`).all(), rows, t);
});

test('the edges: made or signed in exactly a month ago is kept; one second more and it goes', async () => {
  const {sqlite, d1} = db();
  const edge = NOW - EMPTY_ACCOUNT_DAYS * DAY;
  sqlite.prepare('INSERT INTO users(id,recovery_hash,created_at) VALUES(?,?,?)').run('made-at-edge', 'h1', edge);
  sqlite.prepare('INSERT INTO users(id,recovery_hash,created_at) VALUES(?,?,?)').run('made-before-edge', 'h2', edge - 1);
  user(sqlite, 'signed-in-at-edge', 90);
  sqlite.prepare('INSERT INTO sessions(hash,user_id,expires_at,created_at) VALUES(?,?,?,?)').run('s', 'signed-in-at-edge', edge + 30 * DAY, edge);
  user(sqlite, 'session-without-time', 90);   // migration 0006 より前のセッション（created_at が無い）は、ログインに数えない
  sqlite.prepare('INSERT INTO sessions(hash,user_id,expires_at) VALUES(?,?,?)').run('s2', 'session-without-time', NOW + DAY);
  assert.equal(await sweepEmptyAccounts(d1, NOW), 2);
  assert.deepEqual(sqlite.prepare('SELECT id FROM users ORDER BY id').all().map(r => r.id), ['made-at-edge', 'signed-in-at-edge']);
});

test('a sign-in lasts no longer than the month, so a signed-in account is always within the window', () => {
  assert.equal(SESSION_TTL, 7 * DAY);
  assert.ok(SESSION_TTL <= EMPTY_ACCOUNT_DAYS * DAY);
});

test('a record added after the account was picked, before it is deleted, keeps the account', async () => {
  const {sqlite, d1} = db();
  user(sqlite, 'comes-back', 90);
  user(sqlite, 'gone', 90);
  // 選んだ直後（消す前）に、その人がログインして記録を 1 件足す
  const racing = {...d1, prepare(sql) {
    const p = d1.prepare(sql);
    if (!/^SELECT id FROM users u/.test(sql)) return p;
    return {bind: (...v) => ({async all() {
      const r = await p.bind(...v).all();
      sqlite.prepare("INSERT INTO works(user_id,work_key,title,updated_at) VALUES('comes-back','k','題','2026-10-18 00:00:00')").run();
      return r;
    }})};
  }};
  assert.equal(await sweepEmptyAccounts(racing, NOW), 1);
  assert.deepEqual(sqlite.prepare('SELECT id FROM users').all().map(r => r.id), ['comes-back']);
  assert.equal(sqlite.prepare("SELECT count(*) AS n FROM works WHERE user_id='comes-back'").get().n, 1);
});

test('the daily run (scheduled) removes only the empty account and the old fix requests', async () => {
  const {sqlite, d1} = db();
  // scheduled は今の時刻で動くので、ずっと前に作ったアカウントにする
  for (const id of ['empty', 'keeper']) sqlite.prepare('INSERT INTO users(id,recovery_hash,created_at) VALUES(?,?,?)').run(id, 'h-' + id, 1_000_000_000);
  for (const t of RECORD_TABLES) rowFor(sqlite, t, 'keeper');
  // 対応して 1 年たった依頼は消え、未対応の依頼は残る
  sqlite.prepare("INSERT INTO fix_request(stage_id,user_id,kind,message,created_at,status,resolved_at) VALUES('9','keeper','日程','古い','2001-01-01','done','2001-01-02')").run();
  sqlite.prepare("INSERT INTO fix_request(stage_id,user_id,kind,message,created_at) VALUES('9','keeper','日程','未対応','2001-01-01')").run();
  const keep = () => Object.fromEntries(userTables(sqlite).filter(t => t !== 'fix_request').map(t => [t, sqlite.prepare(`SELECT * FROM ${t} WHERE user_id='keeper'`).all()]));
  const before = keep();
  const waits = [];
  await worker.scheduled({}, {DB: d1}, {waitUntil: p => waits.push(p)});
  await Promise.all(waits);
  assert.deepEqual(sqlite.prepare('SELECT id FROM users').all().map(r => r.id), ['keeper']);
  assert.deepEqual(keep(), before);
  assert.deepEqual(sqlite.prepare("SELECT message FROM fix_request WHERE user_id='keeper' ORDER BY id").all().map(r => r.message), ['未対応']);
});
