// 公演修正依頼（migration 0030, src/screens/fixrequest.js）: 保存・1 人 1 日の上限・起案者へのメール（偽の SMTP）。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {setup, step, signIn} from './screens/harness.js';
import {FIX_REQUESTS_PER_USER_DAY} from '../src/free-tier.js';

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
