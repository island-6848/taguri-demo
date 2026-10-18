// D1 storage and account caps (dec-account-cap-counted): sign-ups stop at MAX_ACCOUNTS
// or when D1 reports it is at D1_BYTES_CAP; then writes that grow storage are refused,
// while reading and deleting keep working. Per-user caps of 0021 hold.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {setup, signIn, step} from './screens/harness.js';
import {d1Gate, MAX_ACCOUNTS, NEW_ACCOUNTS_PER_DAY, D1_BYTES_CAP} from '../src/free-tier.js';
import {TERMS_VERSION} from '../src/terms.js';
import {shrinkingAction, shrinkingPath} from '../src/worker.js';

const reset = () => Object.assign(d1Gate, {at: 0, bytes: null, full: false});
/** The harness's D1 with meta.size_after on every result, as D1 returns it. */
function withSize(env, bytes) {
  const prepare = env.DB.prepare;
  env.DB.prepare = sql => {
    const st = prepare(sql);
    const wrap = s => ({...s, bind: (...v) => wrap(s.bind(...v)), all: async () => ({...(await s.all()), meta: {size_after: bytes()}})});
    return wrap(st);
  };
}

test('the caps are the counted ones', () => {
  assert.equal(MAX_ACCOUNTS, 300); assert.equal(NEW_ACCOUNTS_PER_DAY, 30); assert.equal(D1_BYTES_CAP, 4e9);
});

test('sign-up stops at MAX_ACCOUNTS', async () => {
  reset();
  const {env, sqlite} = setup();
  try {
    env.MAX_ACCOUNTS = '2';
    await signIn(env); await signIn(env);
    const res = await step(env, '', {post: '/migration-api/register', body: {agree: TERMS_VERSION}});
    assert.equal(res.status, 503);
    assert.match(res.body.error, /利用者の数に上限/);
  } finally { sqlite.close(); }
});

test('at the storage cap, writes that grow and sign-ups are refused; screens and deletes still work', async () => {
  reset();
  const {env, sqlite} = setup();
  let size = 1e9;
  withSize(env, () => size);
  try {
    const a = await signIn(env);
    const add = await step(env, a, {post: '/api/add_work', body: {title: '舞台いち', date: '2026-01-02'}});
    assert.equal(add.status, 200);
    size = 4.2e9; reset();
    const no = await step(env, a, {post: '/api/add_work', body: {title: '舞台に', date: '2026-01-03'}});
    assert.equal(no.status, 503);
    assert.match(no.body.error, /保存を止めています/);
    assert.equal((await step(env, a, {get: '/api/screen/works'})).status, 200);
    assert.equal((await step(env, a, {post: '/api/drop_work', body: {work_key: add.body.work_key}})).status, 200);
    const reg = await step(env, '', {post: '/migration-api/register', body: {agree: TERMS_VERSION}});
    assert.equal(reg.status, 503);
    assert.match(reg.body.error, /保存できる量の上限/);
  } finally { sqlite.close(); reset(); }
});

// #88: 上限でも、減らす操作（外す・消す・空にする）とログアウト・アカウントの削除は通す。足す操作は止めたまま
test('shrinkingAction / shrinkingPath tell removals from additions', () => {
  for (const [name, input] of [['drop_work', {}], ['agree', {}], ['favourite', {action: 'remove'}], ['decline', {action: 'remove'}],
    ['kind_off', {action: 'remove'}], ['ticket', {action: 'del'}], ['account', {display_name: ''}], ['account', {avatar: ''}]])
    assert.equal(shrinkingAction(name, input), true, name);
  for (const [name, input] of [['add_work', {}], ['favourite', {action: 'add'}], ['decline', {action: 'add'}], ['kind_off', {action: 'add'}],
    ['ticket', {action: 'add'}], ['ticket', {}], ['account', {display_name: 'x'}], ['account', {avatar: 'data:image/png;base64,AA'}], ['rate', {}]])
    assert.equal(shrinkingAction(name, input), false, `${name} ${JSON.stringify(input)}`);
  for (const p of ['/api/record/delete', '/api/logout', '/api/logout/all', '/api/account/delete']) assert.equal(shrinkingPath(p, {}), true, p);
  assert.equal(shrinkingPath('/api/favourite', {remove: true}), true);
  assert.equal(shrinkingPath('/api/reaction', {remove: true}), true);
  for (const [p, input] of [['/api/favourite', {}], ['/api/favourite', {remove: 'true'}], ['/api/reaction', {}], ['/api/record', {}], ['/api/import', {}]])
    assert.equal(shrinkingPath(p, input), false, p);
});

test('at the storage cap, the native screens still let removals through and refuse additions (#88)', async () => {
  reset();
  const {env, sqlite} = setup();
  let size = 1e9;
  withSize(env, () => size);
  try {
    const a = await signIn(env);
    assert.equal((await step(env, a, {post: '/api/favourite', body: {action: 'add', kind: '人', name: '甲'}})).status, 200);
    assert.equal((await step(env, a, {post: '/api/account', body: {display_name: 'あ'}})).status, 200);
    size = 4.2e9; reset();
    const add = await step(env, a, {post: '/api/favourite', body: {action: 'add', kind: '人', name: '乙'}});
    assert.equal(add.status, 503);
    assert.match(add.body.error, /保存を止めています/);
    assert.equal((await step(env, a, {post: '/api/account', body: {display_name: 'い'}})).status, 503);
    assert.equal((await step(env, a, {post: '/api/decline', body: {action: 'add', kind: '人', word: '丙'}})).status, 503);
    assert.equal((await step(env, a, {post: '/api/favourite', body: {action: 'remove', kind: '人', name: '甲'}})).status, 200);
    assert.equal((await step(env, a, {post: '/api/account', body: {display_name: ''}})).status, 200);
    // 無いものを外しても、行は増えない
    const rows = sqlite.prepare('SELECT count(*) AS n FROM app_setting').get().n;
    assert.equal((await step(env, a, {post: '/api/decline', body: {action: 'remove', kind: '人', word: '丁'}})).status, 200);
    assert.equal((await step(env, a, {post: '/api/kind_off', body: {action: 'remove', key: '#原作\tオリジナル'}})).status, 200);
    assert.equal(sqlite.prepare('SELECT count(*) AS n FROM app_setting').get().n, rows);
    assert.equal(sqlite.prepare("SELECT count(*) AS n FROM favourites WHERE name='甲'").get().n, 0);
    // ログアウト・すべての端末からログアウト・アカウントの削除
    assert.equal((await step(env, a, {post: '/api/logout', body: {}})).status, 200);
    const b = await (async () => { size = 1e9; reset(); const c = await signIn(env); size = 4.2e9; reset(); return c; })();
    assert.equal((await step(env, b, {post: '/api/logout/all', body: {}})).status, 200);
    const c = await (async () => { size = 1e9; reset(); const x = await signIn(env); size = 4.2e9; reset(); return x; })();
    const del = await step(env, c, {post: '/migration-api/account/delete', body: {confirm: '削除'}});
    assert.equal(del.status, 200, JSON.stringify(del.body));
    assert.equal(del.body.deleted, true);
  } finally { sqlite.close(); reset(); }
});

test('at the storage cap, the Worker API lets removals and sign-outs through and refuses additions (#88)', async () => {
  reset();
  const {env, sqlite} = setup();
  env.NATIVE_UI = ''; env.ORIGINAL_UI_BRIDGE = 'false';
  let size = 1e9;
  withSize(env, () => size);
  try {
    const a = await signIn(env);
    assert.equal((await step(env, a, {post: '/api/favourite', body: {kind: '人', name: '甲'}})).status, 200);
    assert.equal((await step(env, a, {post: '/api/reaction', body: {stage_id: '1', status: 'interest'}})).status, 200);
    size = 4.2e9; reset();
    for (const s of [{post: '/api/favourite', body: {kind: '人', name: '乙'}}, {post: '/api/reaction', body: {stage_id: '2', status: 'interest'}},
      {post: '/api/record', body: {id: 'r1', title: 'x', date: '2026-01-01'}}]) {
      const got = await step(env, a, s);
      assert.equal(got.status, 503, JSON.stringify(s));
      assert.match(got.body.error, /保存を止めています/);
    }
    assert.equal((await step(env, a, {post: '/api/favourite', body: {kind: '人', name: '甲', remove: true}})).status, 200);
    assert.equal((await step(env, a, {post: '/api/reaction', body: {stage_id: '1', status: 'interest', remove: true}})).status, 200);
    assert.equal(sqlite.prepare('SELECT count(*) AS n FROM favourites').get().n, 0);
    assert.equal(sqlite.prepare('SELECT count(*) AS n FROM reactions').get().n, 0);
    assert.equal((await step(env, a, {post: '/api/logout/all', body: {}})).status, 200);
    assert.equal(sqlite.prepare('SELECT count(*) AS n FROM sessions').get().n, 0);
    size = 1e9; reset();
    const b = await signIn(env);
    size = 4.2e9; reset();
    assert.equal((await step(env, b, {post: '/api/logout', body: {}})).status, 200);
    assert.equal(sqlite.prepare('SELECT count(*) AS n FROM sessions').get().n, 0);
    size = 1e9; reset();
    const c = await signIn(env);
    size = 4.2e9; reset();
    const del = await step(env, c, {post: '/api/account/delete', body: {confirm: '削除'}});
    assert.equal(del.status, 200, JSON.stringify(del.body));
  } finally { sqlite.close(); reset(); }
});

test('0021: one account keeps at most 2,000 visit notes and 200 search requests', () => {
  const {sqlite} = setup();
  try {
    sqlite.exec("INSERT INTO users(id,recovery_hash,created_at) VALUES('u','h',0)");
    const v = sqlite.prepare("INSERT INTO visit_note(user_id,uid,note,updated_at) VALUES('u',?,'x','t') ON CONFLICT(user_id,uid) DO UPDATE SET note=excluded.note");
    for (let i = 0; i < 2000; i++) v.run(`u${i}`);
    v.run('u5');                                   // updating an existing one is fine
    assert.throws(() => v.run('u2000'), /visit_note limit/);
    const s = sqlite.prepare("INSERT INTO search_request(user_id,qkey,query,source,created_at) VALUES('u',?,'q','s','t')");
    for (let i = 0; i < 200; i++) s.run(`q${i}`);
    assert.throws(() => s.run('q200'), /search_request limit/);
  } finally { sqlite.close(); }
});
