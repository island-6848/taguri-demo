// 公演修正依頼（migration 0030, src/screens/fixrequest.js）: 保存・1 人 1 日の上限・起案者へのメール（偽の SMTP）。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {setup, step, signIn} from './screens/harness.js';
import {FIX_REQUESTS_PER_USER_DAY, FIX_OPEN_PER_USER, FIX_STORED_PER_USER, FIX_STORED_TOTAL} from '../src/free-tier.js';
import {purgeFixRequests, PURGED} from '../src/screens/fixrequest.js';

const here = p => new URL(p, import.meta.url).pathname;
const FIXTURE = JSON.parse(execFileSync('python3', [here('./screens/recommend_fixture.py')], {encoding: 'utf8', maxBuffer: 64 * 1024 * 1024}));

/** A socket-like pair that plays Gmail's side of SMTP and keeps what it was sent. */
function fakeSmtp(seen, {authCode = 235} = {}) {
  const enc = new TextEncoder(), dec = new TextDecoder();
  let push;
  const readable = new ReadableStream({start(c) { push = s => c.enqueue(enc.encode(s)); push('220 smtp.gmail.com ESMTP\r\n'); }});
  let inData = false, buf = '';
  const writable = new WritableStream({write(chunk) {
    buf += dec.decode(chunk);
    let i;
    while ((i = buf.indexOf('\r\n')) >= 0) {
      const line = buf.slice(0, i); buf = buf.slice(i + 2);
      seen.lines.push(line);
      if (inData) { if (line === '.') { inData = false; push('250 2.0.0 OK\r\n'); } else seen.data.push(line); continue; }
      if (line.startsWith('EHLO')) push('250-smtp.gmail.com\r\n250-AUTH PLAIN\r\n250 SMTPUTF8\r\n');
      else if (line.startsWith('AUTH')) push(`${authCode} auth\r\n`);
      else if (line.startsWith('MAIL') || line.startsWith('RCPT')) push('250 OK\r\n');
      else if (line === 'DATA') { inData = true; push('354 go\r\n'); }
    }
  }});
  return {readable, writable, close: async () => {}};
}

test('a request is saved, the owner is mailed (no requester details), and one user has a daily cap', async () => {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  const seen = {lines: [], data: []};
  Object.assign(env, {SMTP_USER: 'owner@gmail.com', SMTP_PASS: 'app-pass', SMTP_OPEN: async () => fakeSmtp(seen)});
  const a = await signIn(env);
  try {
    const r = await step(env, a, {post: '/api/fix_request', body: {stage_id: '101', kind: '料金', message: '一般は 6,000 円です https://example.com'}});
    assert.equal(r.status, 200, JSON.stringify(r.body));
    const row = sqlite.prepare('SELECT stage_id,kind,message,status,mailed FROM fix_request').get();
    assert.deepEqual({...row}, {stage_id: '101', kind: '料金', message: '一般は 6,000 円です https://example.com', status: 'open', mailed: 1});
    assert.ok(seen.lines.includes(`AUTH PLAIN ${btoa('\0owner@gmail.com\0app-pass')}`));
    assert.ok(seen.lines.includes('RCPT TO:<owner@gmail.com>'));
    const subject = seen.data.find(l => l.startsWith('Subject: ='));
    const b64 = /=\?UTF-8\?B\?(.*)\?=/.exec(subject)[1];
    assert.match(new TextDecoder().decode(Uint8Array.from(atob(b64), c => c.charCodeAt(0))), /^【たぐり】公演修正依頼: .+（料金）$/);
    const body = new TextDecoder().decode(Uint8Array.from(atob(seen.data.slice(seen.data.indexOf('') + 1).join('')), c => c.charCodeAt(0)));
    assert.match(body, /依頼 #1[\s\S]*違うところ: 料金[\s\S]*一般は 6,000 円です/);
    assert.doesNotMatch(body, new RegExp(sqlite.prepare('SELECT user_id FROM fix_request').get().user_id));
    // bad input
    assert.equal((await step(env, a, {post: '/api/fix_request', body: {stage_id: '101', kind: '天気', message: 'x'}})).status, 400);
    assert.equal((await step(env, a, {post: '/api/fix_request', body: {stage_id: '101', kind: '日程', message: ' '}})).status, 400);
    // daily cap per user
    for (let i = 1; i < FIX_REQUESTS_PER_USER_DAY; i++) assert.equal((await step(env, a, {post: '/api/fix_request', body: {stage_id: '101', kind: 'その他', message: 'm' + i}})).status, 200);
    const over = await step(env, a, {post: '/api/fix_request', body: {stage_id: '101', kind: 'その他', message: 'over'}});
    assert.equal(over.status, 400);
    assert.match(over.body.error, /1 日に送れる依頼は/);
  } finally { sqlite.close(); }
});

test('without mail settings, or when Gmail refuses, the request is still saved (mailed=0)', async () => {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  const a = await signIn(env);
  try {
    assert.equal((await step(env, a, {post: '/api/fix_request', body: {stage_id: '101', kind: '日程', message: '休演日が違う'}})).status, 200);
    Object.assign(env, {SMTP_USER: 'owner@gmail.com', SMTP_PASS: 'wrong', SMTP_OPEN: async () => fakeSmtp({lines: [], data: []}, {authCode: 535})});
    assert.equal((await step(env, a, {post: '/api/fix_request', body: {stage_id: '101', kind: '日程', message: 'もう 1 件'}})).status, 200);
    assert.deepEqual(sqlite.prepare('SELECT mailed FROM fix_request ORDER BY id').all().map(r => r.mailed), [0, 0]);
  } finally { sqlite.close(); }
});

// issue #129: the stored requests are bounded (per user open / stored, overall) inside the INSERT itself,
// resolved bodies and rows expire, and deleting the account clears the requester and the text.
test('open, stored-per-user and overall caps hold, and are checked in the INSERT', async () => {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  const a = await signIn(env);
  const send = m => step(env, a, {post: '/api/fix_request', body: {stage_id: '101', kind: 'その他', message: m}});
  const earlier = (n, status) => {
    for (let i = 0; i < n; i++) sqlite.prepare("INSERT INTO fix_request(stage_id,user_id,kind,message,created_at,status) SELECT '101',user_id,'その他','old','2026-01-01T00:00:00.000Z',? FROM sessions LIMIT 1").run(status);
  };
  try {
    // open requests from earlier days count; FIX_OPEN_PER_USER of them stop new ones
    earlier(FIX_OPEN_PER_USER, 'open');
    let r = await send('one more');
    assert.equal(r.status, 400);
    assert.match(r.body.error, /まだ確かめていない依頼が/);
    sqlite.exec("UPDATE fix_request SET status='done', resolved_at='2026-01-02T00:00:00Z'");
    assert.equal((await send('now fine')).status, 200);
    // stored per user: resolved ones count too, until they expire
    earlier(FIX_STORED_PER_USER - FIX_OPEN_PER_USER - 1, 'done');
    r = await send('too many kept');
    assert.equal(r.status, 400);
    assert.match(r.body.error, /送れる依頼は/);
    assert.equal(sqlite.prepare('SELECT count(*) AS n FROM fix_request').get().n, FIX_STORED_PER_USER);
    // overall: someone else is stopped once the table holds FIX_STORED_TOTAL rows
    sqlite.exec('DELETE FROM fix_request');
    const b = await signIn(env);
    sqlite.prepare(`WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i+1 FROM n WHERE i<?)
      INSERT INTO fix_request(stage_id,user_id,kind,message,created_at,status) SELECT '101','x'||i,'その他','m','2026-01-01T00:00:00.000Z','done' FROM n`).run(FIX_STORED_TOTAL);
    r = await step(env, b, {post: '/api/fix_request', body: {stage_id: '101', kind: '日程', message: 'full'}});
    assert.equal(r.status, 400);
    assert.match(r.body.error, /受け付けられません/);
    assert.equal(sqlite.prepare('SELECT count(*) AS n FROM fix_request').get().n, FIX_STORED_TOTAL);
  } finally { sqlite.close(); }
});

test('resolved requests lose their text after 30 days and the row after 180; open ones stay', async () => {
  const {env, sqlite} = setup();
  const now = Date.parse('2026-10-18T00:00:00Z');
  const ago = d => new Date(now - d * 86400_000).toISOString().replace('.000Z', 'Z');
  const add = (status, resolved) => sqlite.prepare("INSERT INTO fix_request(stage_id,user_id,kind,message,created_at,status,resolved_at) VALUES('1','u','その他','本文','2025-01-01T00:00:00.000Z',?,?)").run(status, resolved);
  try {
    add('open', null); add('done', ago(10)); add('done', ago(31)); add('dropped', ago(100)); add('done', ago(181));
    assert.deepEqual(await purgeFixRequests(env.DB, now), {cleared: 3, removed: 1});
    assert.deepEqual(sqlite.prepare('SELECT status, message FROM fix_request ORDER BY id').all().map(r => [r.status, r.message]),
      [['open', '本文'], ['done', '本文'], ['done', PURGED], ['dropped', PURGED]]);
    assert.deepEqual(await purgeFixRequests(env.DB, now), {cleared: 0, removed: 0});   // nothing left to change
  } finally { sqlite.close(); }
});

test('deleting the account clears the requester and the text of their requests', async () => {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  const a = await signIn(env);
  try {
    assert.equal((await step(env, a, {post: '/api/fix_request', body: {stage_id: '101', kind: '日程', message: '電話は 000-0000-0000'}})).status, 200);
    assert.equal((await step(env, a, {post: '/migration-api/account/delete', body: {confirm: '削除'}})).status, 200);
    assert.deepEqual({...sqlite.prepare('SELECT user_id, message FROM fix_request').get()}, {user_id: '', message: '（アカウント削除により消去）'});
  } finally { sqlite.close(); }
});
