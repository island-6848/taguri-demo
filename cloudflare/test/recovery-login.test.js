// 復旧コードでのログイン（ふつうの /login）。#134 の通し検証で、パスキーで始めた人に渡す復旧コードを
// 入れる欄が、削除（?purpose=delete）と結び付け（?link=1）の画面にしか無いと分かった。
// ログインしていないと /migration-data/ の欄も開けないので、端末をなくすと戻る道が無かった。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import worker from '../src/worker.js';
import {setup} from './screens/harness.js';
import {TERMS_VERSION} from '../src/terms.js';

const SRC = readFileSync(new URL('../src/client/login.js', import.meta.url), 'utf8');
const BUNDLE = readFileSync(new URL('../public/vendor/firebase-login.js', import.meta.url), 'utf8');
const HTML = readFileSync(new URL('../public/login.html', import.meta.url), 'utf8');

test('the plain login page shows the recovery-code form and signs in with it', () => {
  const fn = SRC.slice(SRC.indexOf('function setupRecovery()'));
  assert.ok(fn.length > 0 && /^setupRecovery\(\);$/m.test(SRC), 'setupRecovery is defined and called');
  const body = fn.slice(0, fn.indexOf('\n}\n'));
  assert.match(body, /if \(DELETE_MODE \|\| LINK_MODE\) return;/);           // those modes have their own handler
  assert.match(body, /\$\('#recovery-login'\)\.hidden = false/);
  assert.match(body, /postJSON\('\/migration-api\/recover', \{code: \$\('#recovery-input'\)\.value\.trim\(\)\}\)/);
  assert.match(body, /signedIn\('ログインしました。'\)/);
  // the bundle served to browsers was rebuilt from it (npm run build:login)
  assert.equal((BUNDLE.match(/\/migration-api\/recover/g) || []).length, 3, 'delete, link and the plain login');
  // 起案者の指示 2026-10-18「ログイン画面の『復旧コードでログイン』は、『メールでログイン』の下に点線を引いて、その下に置いて
  // （独立した欄を設けないで）。」: 独立した札（auth-card）をやめ、ログインの欄（#login）の中、メールの欄の下に置く
  assert.match(HTML, /<form id="recovery-login" class="mailrow recov" hidden><label>復旧コードでログイン<span class="mailin"><input id="recovery-input"/);
  const login = HTML.slice(HTML.indexOf('<section id="login"'), HTML.indexOf('</section>', HTML.indexOf('<section id="login"')));
  assert.ok(login.indexOf('id="email-form"') > 0 && login.indexOf('id="recovery-login"') > login.indexOf('id="email-form"'), 'メールでログインの下、ログインの欄の中');
  assert.doesNotMatch(HTML, /id="recovery-login" class="auth-card"/);
});

test('a recovery code signs in without a session (what the form posts)', async () => {
  const {env, sqlite} = setup();
  const ORIGIN = 'https://taguri.example';
  const post = (path, body, cookie = '') => worker.fetch(new Request(ORIGIN + path, {method: 'POST', headers: {origin: ORIGIN, 'content-type': 'application/json', cookie}, body: JSON.stringify(body)}), env);
  try {
    const reg = await post('/migration-api/register', {agree: TERMS_VERSION});
    const {recovery_code} = await reg.json();
    const back = await post('/migration-api/recover', {code: recovery_code});
    assert.equal(back.status, 200);
    assert.match(back.headers.get('set-cookie'), /^taguri_session=/);
    assert.equal((await post('/migration-api/recover', {code: 'x'.repeat(64)})).status, 401);
  } finally { sqlite.close(); }
});
