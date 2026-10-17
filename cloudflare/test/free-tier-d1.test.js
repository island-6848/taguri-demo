// D1 storage and account caps (dec-account-cap-counted): sign-ups stop at MAX_ACCOUNTS
// or when D1 reports it is at D1_BYTES_CAP; then writes that grow storage are refused,
// while reading and deleting keep working. Per-user caps of 0021 hold.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {setup, signIn, step} from './screens/harness.js';
import {d1Gate, MAX_ACCOUNTS, NEW_ACCOUNTS_PER_DAY, D1_BYTES_CAP} from '../src/free-tier.js';
import {TERMS_VERSION} from '../src/terms.js';

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
