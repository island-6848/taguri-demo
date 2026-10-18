// 本番は配備のたびに、まだ当てていない migration を当てる（Workers Builds の配備の命令:
// `npx wrangler d1 migrations apply taguri-demo --remote && npx wrangler deploy`）。issue #137:
// 利用者の記録がある DB に後の migration を当てても、本人の行と値が 1 つも消えず・変わらないことを確かめる。
//
// 0001 から N まで当てた DB に、その時点の利用者の表（user_id の列がある表と users）すべてへ 2 人分の行を入れ、
// 残りの migration を当てて比べる。N は 1 から最後の 1 つ前まで全部。新しい migration を足すと自動で対象になる。
// - 前からある列: 値がそのまま（意図して書き換える migration は REWRITES に、どう変わるかを書く）
// - 新しい列: 宣言した既定値（埋め直す migration は BACKFILLS に、どの値になるかを書く）
// - 行の数が同じ、外部キーが壊れていない（D1 は外部キーを確かめる。users を作り直すと ON DELETE CASCADE で全部消える）
// - 行のある DB で当てて失敗しない（例: 既定値の無い NOT NULL 列を足すと、空の DB では通り、本番では配備ごと止まる）
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync, readdirSync} from 'node:fs';

const DIR = new URL('../migrations/', import.meta.url);
const FILES = readdirSync(DIR).filter(n => /^\d{4}\.sql$/.test(n)).sort();
const sql = f => readFileSync(new URL(f, DIR), 'utf8');

// 意図して前からある値を書き換える migration（file → 表 → 前の行から後の行を作る関数）
const REWRITES = {
  // 興味ありを押した画面の付け直し（0025.sql の本文）
  '0025.sql': {reaction: r => r.interest === 1 && ['screen', 'screen_tour'].includes(r.source) && r.updated_at < '2026-10-15T23:39:00'
    ? {...r, source: r.source === 'screen_tour' ? 'reminder_tour' : 'reminder'} : r},
};
// 既定値でなく、前からある値から埋める新しい列（表.列 → 前の行から値を作る関数）
const BACKFILLS = {
  'works.rated_at': r => r.verdict !== null && r.verdict !== '' ? r.updated_at : null,   // 0034.sql
};
// 調べた migration に、書き換えの UPDATE・DELETE を足したら、上の 2 つにも書く（ここで気付けるように数える）
const WRITING = FILES.filter(f => /^\s*(UPDATE|DELETE|DROP\s+TABLE|INSERT\s+OR\s+REPLACE)\b/im.test(sql(f).replace(/^\s*--.*$/gm, '')));

const USERS = ['user-a', 'user-b'];
const ROWS = 3;

function open() {
  const db = new DatabaseSync(':memory:', {enableForeignKeyConstraints: true});
  db.exec('PRAGMA foreign_keys=ON');
  return db;
}
const tablesOf = db => db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").all().map(r => r.name);
const colsOf = (db, t) => db.prepare(`PRAGMA table_info(${t})`).all();
const userTables = db => tablesOf(db).filter(t => t === 'users' || colsOf(db, t).some(c => c.name === 'user_id'));

/** 列の値。本物らしい形にしたい列（CHECK・UNIQUE・migration が見る列）だけ決め、あとは表・列・人・行が分かる値 */
function value(t, c, uid, i) {
  const n = USERS.indexOf(uid) * 10 + i;
  const special = {
    'users.id': uid, 'users.recovery_hash': `hash-${uid}`, 'users.firebase_uid': i === 0 ? `fb-${uid}` : null,
    'users.created_at': 1_760_000_000 + n,
    'reactions.status': ['interest', 'no', 'owned'][i],
    'webauthn_challenges.purpose': ['register', 'login', 'login'][i],
    // 評価のある行・無い行（NULL）・空の行（0034 の埋め方の 3 通り）
    'works.verdict': ['◎', null, ''][i], 'works.updated_at': `2026-10-0${i + 1} 12:00:00`,
    // 0025 で付け直す行・#28 より後で触らない行・別の画面の行
    'reaction.interest': 1, 'reaction.source': ['screen', 'screen_tour', 'search'][i],
    'reaction.updated_at': ['2026-10-10T10:00:00', '2026-10-16T10:00:00', '2026-10-01T00:00:00'][i],
    'fix_request.id': n + 1,
  }[`${t}.${c.name}`];
  if (special !== undefined) return special;
  if (c.name === 'user_id') return uid;
  if (/INT/i.test(c.type)) return 100 + n;
  if (/REAL/i.test(c.type)) return n + 0.25;
  return `${t}.${c.name}.${uid}.${i}`;
}
// 主キーが利用者だけの表（users・rec_cache）は 1 人 1 行
const oneRow = (db, t) => { const pk = colsOf(db, t).filter(c => c.pk).map(c => c.name); return pk.length === 1 && ['id', 'user_id'].includes(pk[0]); };
function seed(db) {
  for (const t of ['users', ...userTables(db).filter(t => t !== 'users')]) {
    const cols = colsOf(db, t);
    const put = db.prepare(`INSERT INTO ${t}(${cols.map(c => c.name).join(',')}) VALUES(${cols.map(() => '?').join(',')})`);
    for (const uid of USERS) for (let i = 0; i < (oneRow(db, t) ? 1 : ROWS); i++) put.run(...cols.map(c => value(t, c, uid, i)));
  }
}
const keyOf = (db, t) => { const pk = colsOf(db, t).filter(c => c.pk).sort((a, b) => a.pk - b.pk).map(c => c.name); return pk.length ? pk : colsOf(db, t).map(c => c.name); };
function snapshot(db) {
  return Object.fromEntries(userTables(db).map(t => [t, {cols: colsOf(db, t).map(c => c.name),
    rows: db.prepare(`SELECT * FROM ${t} ORDER BY ${keyOf(db, t).join(',')}`).all().map(r => ({...r}))}]));
}
/** 宣言した既定値（PRAGMA の dflt_value）を値にする。式の既定値は BACKFILLS に書く */
function literal(dflt, where) {
  if (dflt === null) return null;
  const s = /^'(.*)'$/s.exec(dflt);
  if (s) return s[1].replaceAll("''", "'");
  if (/^-?\d+(\.\d+)?$/.test(dflt)) return Number(dflt);
  if (/^NULL$/i.test(dflt)) return null;
  throw new Error(`${where}: 既定値 ${dflt} の値を BACKFILLS に書く`);
}

// 書き換えの文を持つ migration と、この試験での扱い。足したら、ここと REWRITES・BACKFILLS に書く
const KNOWN_WRITING = {
  '0025.sql': 'REWRITES（reaction.source の付け直し）',
  '0030.sql': 'トリガーの本文（アカウントを消したときだけ fix_request を書き換える。migration を当てるときは動かない）',
  '0034.sql': 'BACKFILLS（works.rated_at）',
};
test('every migration that rewrites stored values is known to this test', () => {
  assert.deepEqual(WRITING, Object.keys(KNOWN_WRITING), '値を書き換える migration を足したら、REWRITES・BACKFILLS に期待する値を書き、KNOWN_WRITING にも足す');
});

for (let cut = 1; cut < FILES.length; cut++) {
  test(`user rows put in after ${FILES[cut - 1]} survive ${FILES.slice(cut).length} later migration(s) unchanged`, () => {
    const db = open();
    for (const f of FILES.slice(0, cut)) db.exec(sql(f));
    seed(db);
    const before = snapshot(db);
    const beforeCols = Object.fromEntries(Object.keys(before).map(t => [t, colsOf(db, t)]));
    for (const f of FILES.slice(cut)) {
      try { db.exec(sql(f)); } catch (e) { assert.fail(`${f} fails on a database that already has user rows (after ${FILES[cut - 1]}): ${e.message}`); }
    }
    // 期待する後の値: 前の行に、残りの migration の書き換えを順に当てる
    const expect = structuredClone(before);
    for (const f of FILES.slice(cut)) for (const [t, fn] of Object.entries(REWRITES[f] || {})) if (expect[t]) expect[t].rows = expect[t].rows.map(fn);
    for (const [t, {cols}] of Object.entries(before)) {
      assert.ok(tablesOf(db).includes(t), `${t} が消えた`);
      const all = colsOf(db, t);
      for (const c of cols) assert.ok(all.some(x => x.name === c), `${t}.${c} が消えた`);
      const now = db.prepare(`SELECT * FROM ${t} ORDER BY ${keyOf(db, t).join(',')}`).all().map(r => ({...r}));
      assert.equal(now.length, before[t].rows.length, `${t} の行の数`);
      // 前からある列はそのまま（REWRITES の分だけ変わる）
      assert.deepEqual(now.map(r => Object.fromEntries(cols.map(c => [c, r[c]]))), expect[t].rows, `${t}: 前からある値`);
      // 新しい列は既定値か、BACKFILLS の値
      for (const c of all.filter(x => !beforeCols[t].some(b => b.name === x.name))) {
        const fill = BACKFILLS[`${t}.${c.name}`];
        now.forEach((r, i) => assert.deepEqual(r[c.name], fill ? fill(expect[t].rows[i]) : literal(c.dflt_value, `${t}.${c.name}`),
          `${t}.${c.name}（${FILES[cut - 1]} の後に入れた行 ${i}）`));
      }
    }
    assert.deepEqual(db.prepare('PRAGMA foreign_key_check').all(), [], '外部キー');
    db.close();
  });
}

test('the backfill of works.rated_at (0034) and of users.tokens_valid_after (0033) on rows written at 0032: rated rows start from updated_at, others stay empty', () => {
  const db = open();
  for (const f of FILES.filter(f => f < '0033.sql')) db.exec(sql(f));
  seed(db);
  db.exec(sql('0033.sql'));
  db.exec(sql('0034.sql'));
  const got = db.prepare("SELECT verdict, updated_at, rated_at FROM works WHERE user_id='user-a' ORDER BY work_key").all().map(r => ({...r}));
  assert.deepEqual(got, [
    {verdict: '◎', updated_at: '2026-10-01 12:00:00', rated_at: '2026-10-01 12:00:00'},
    {verdict: null, updated_at: '2026-10-02 12:00:00', rated_at: null},
    {verdict: '', updated_at: '2026-10-03 12:00:00', rated_at: null},
  ]);
  // users.tokens_valid_after（0033）は空で始まる（すべての端末でログアウトしたことがない）
  assert.deepEqual(db.prepare('SELECT DISTINCT tokens_valid_after AS t FROM users').all().map(r => r.t), [null]);
  db.close();
});

test('the test would notice a migration that loses user rows (a table rebuilt without its rows, a cascade)', () => {
  const db = open();
  for (const f of FILES) db.exec(sql(f));
  seed(db);
  const n = db.prepare('SELECT count(*) AS n FROM works').get().n;
  // users を作り直す（よくある「列を変えるための作り直し」）と、ON DELETE CASCADE で利用者の行が全部消える
  db.exec('CREATE TABLE users_new AS SELECT * FROM users; DROP TABLE users; ALTER TABLE users_new RENAME TO users;');
  assert.notEqual(db.prepare('SELECT count(*) AS n FROM works').get().n, n);
  db.close();
});
