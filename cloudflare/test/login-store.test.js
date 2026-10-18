// メールのリンク用にブラウザーへ控えるもの（src/client/login-store.js）に期限がある（issue #132）
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {loginStore, PENDING_KEYS, PENDING_TTL_MS, SAVED_AT_KEY} from '../src/client/login-store.js';

const fakeStorage = () => { const m = new Map(); return {m, getItem: k => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)), removeItem: k => m.delete(k)}; };

test('the saved address, intent and consent are dropped once an hour has passed', () => {
  const s = fakeStorage();
  let t = 1_000_000;
  const store = loginStore(() => s, () => t);
  store.set('someone@example.com'); store.setIntent('signup'); store.setAgree('2026-10-18-2');
  t += PENDING_TTL_MS - 1;
  store.expire();
  assert.equal(store.get(), 'someone@example.com');
  assert.equal(store.intent(), 'signup');
  t += 1;
  store.expire();
  assert.equal(store.get(), '');
  assert.equal(store.intent(), 'login');           // 期限切れのあとは、アカウントを作らないログインの扱い
  assert.equal(store.agree(), undefined);
  assert.equal(s.m.size, 0);
});

test('entries without a time (saved before this change) or from the future are dropped; nothing saved stays nothing', () => {
  const s = fakeStorage();
  const store = loginStore(() => s, () => 5_000);
  s.setItem('taguri_login_email', 'old@example.com');
  store.expire();
  assert.equal(s.m.size, 0);
  store.set('a@example.com');
  s.setItem(SAVED_AT_KEY, '999999999');
  store.expire();
  assert.equal(s.m.size, 0);
  store.expire();
  assert.equal(s.m.size, 0);
});

test('clear removes every key, and a blocked storage never throws', () => {
  const s = fakeStorage();
  const store = loginStore(() => s);
  store.set('a@example.com'); store.setIntent('login'); store.setAgree('v');
  store.clear();
  for (const k of PENDING_KEYS) assert.equal(s.getItem(k), null);
  const blocked = loginStore(() => { throw new Error('SecurityError'); });
  for (const f of ['get', 'set', 'clear', 'expire', 'intent', 'setIntent', 'agree', 'setAgree']) assert.doesNotThrow(() => blocked[f]('x'));
  assert.equal(blocked.intent(), 'login');
});

test('signing out from the account page clears the same keys', () => {
  const app = readFileSync(new URL('../../web/app.js', import.meta.url), 'utf8');
  for (const k of PENDING_KEYS) assert.ok(app.includes(`"${k}"`), k);
});
