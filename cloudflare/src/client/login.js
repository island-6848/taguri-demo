// Login page (/login). Bundled to public/vendor/firebase-login.js by
// `npm run build:login`; the Firebase SDK is vendored so the page needs no
// third-party script origin.
//
// Firebase is used only to prove who the user is. The ID token goes straight
// to the Worker (/api/auth/firebase), which issues taguri's own HttpOnly
// session, then the Firebase session is dropped. inMemoryPersistence keeps
// Firebase tokens out of localStorage/IndexedDB.
import {initializeApp} from 'firebase/app';
import {
  initializeAuth, inMemoryPersistence, browserPopupRedirectResolver,
  GoogleAuthProvider, signInWithPopup, sendSignInLinkToEmail,
  isSignInWithEmailLink, signInWithEmailLink, signOut, deleteUser,
} from 'firebase/auth';
import {startAuthentication, startRegistration, browserSupportsWebAuthn} from '@simplewebauthn/browser';

const EMAIL_KEY = 'taguri_login_email';
// /login?purpose=delete: sign in again, then delete the account (R7).
const PARAMS = new URLSearchParams(location.search);
const DELETE_MODE = PARAMS.get('purpose') === 'delete';
// /login?link=1 (from the account page): link Google or an email to the
// account signed in now. Only this flag asks the server to link.
const LINK_MODE = !DELETE_MODE && PARAMS.get('link') === '1';
// Where to go after signing in: only a path on this site. Same rule as the
// Worker's safeNext: browsers drop tabs/newlines and read "\" as "/", so the
// value is parsed and must stay on this origin.
function safeNext(v) {
  if (typeof v !== 'string' || !v.startsWith('/') || /[\u0000-\u001f\u007f\\]/.test(v)) return '/';
  let url;
  try { url = new URL(v, location.origin); } catch { return '/'; }
  if (url.origin !== location.origin || url.pathname.startsWith('/login')) return '/';
  return url.pathname + url.search + url.hash;
}
const NEXT = safeNext(PARAMS.get('next'));
// Keep purpose/link/next across the email link round trip.
const loginUrl = () => {
  const q = new URLSearchParams();
  if (DELETE_MODE) q.set('purpose', 'delete');
  else { if (LINK_MODE) q.set('link', '1'); if (NEXT !== '/') q.set('next', NEXT); }
  const s = q.toString();
  return '/login' + (s ? '?' + s : '');
};
let firebaseUser = null;   // kept only in delete mode, to delete the Google-side user too
const $ = s => document.querySelector(s);
const say = (text, bad = false) => { const s = $('#status'); s.textContent = text; s.classList.toggle('bad', bad); };
const busy = on => document.querySelectorAll('button, input').forEach(el => { el.disabled = on; });
const store = {
  get: () => { try { return localStorage.getItem(EMAIL_KEY) || ''; } catch { return ''; } },
  set: v => { try { localStorage.setItem(EMAIL_KEY, v); } catch {} },
  clear: () => { try { localStorage.removeItem(EMAIL_KEY); } catch {} },
};

async function exchange(auth, credential) {
  const idToken = await credential.user.getIdToken();
  const res = await fetch('/api/auth/firebase', {method: 'POST', credentials: 'same-origin',
    headers: {'content-type': 'application/json'}, body: JSON.stringify({id_token: idToken, link: LINK_MODE})});
  if (DELETE_MODE) firebaseUser = credential.user;
  else await signOut(auth).catch(() => {});
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'ログインできませんでした。');
  if (LINK_MODE) { say(data.linked ? '結び付けました。次からは Google かメールでログインできます。' : 'すでに結び付いています。'); location.replace(NEXT === '/' ? '/account' : NEXT); return; }
  signedIn('ログインしました。');
}

// After any sign-in: go to the records, or (delete mode) ask for confirmation.
function signedIn(message) {
  if (LINK_MODE) {
    busy(false);
    $('#recovery-login').hidden = true;
    say('本人確認ができました。続けて10分以内に、Google かメールでログインすると結び付きます。');
    return;
  }
  if (!DELETE_MODE) { say(message); location.replace(NEXT); return; }
  busy(false);
  for (const id of ['#login', '#passkey', '#recovery-login']) $(id).hidden = true;
  $('#delete-confirm').hidden = false;
  say('本人確認ができました。10分以内に削除してください。');
}

// Firebase error codes -> what the user can do about it. Never echo raw errors.
function explain(e) {
  const code = String(e?.code || '');
  if (code.includes('popup-closed') || code.includes('cancelled-popup')) return 'ログインを取りやめました。';
  if (code.includes('popup-blocked')) return 'ポップアップが止められました。ブラウザの設定で許可してから、もう一度押してください。';
  if (code.includes('invalid-email')) return 'メールアドレスを確認してください。';
  if (code.includes('invalid-action-code') || code.includes('expired-action-code')) return 'このリンクは使えません。もう一度メールを送ってください。';
  if (code.includes('too-many-requests') || code.includes('quota')) return '試行が多すぎます。しばらく待ってから試してください。';
  if (code.includes('network')) return '通信できませんでした。接続を確かめてください。';
  return e instanceof Error && !code ? e.message : 'ログインできませんでした。もう一度お試しください。';
}

async function main() {
  const res = await fetch('/api/auth/config', {credentials: 'omit'});
  if (!res.ok) { $('#google').disabled = true; $('#email-form').hidden = true; return; }
  const config = await res.json();
  const app = initializeApp({apiKey: config.apiKey, authDomain: config.authDomain, projectId: config.projectId});
  const auth = initializeAuth(app, {persistence: inMemoryPersistence, popupRedirectResolver: browserPopupRedirectResolver});
  auth.languageCode = 'ja';

  // Returning from the email link.
  const link = location.href;
  if (isSignInWithEmailLink(auth, link)) {
    history.replaceState(null, '', loginUrl());   // drop the one-time code
    let email = store.get();
    // Opened on another device/browser: ask again instead of trusting the URL.
    // Linking only happens in the browser that asked for the link, so a link
    // someone else sent cannot attach their email to this account.
    if (!email && LINK_MODE) say('結び付けは、メールを送ったのと同じブラウザでリンクを開いてください。', true);
    else if (!email) email = (prompt('確認のため、リンクを送ったメールアドレスを入力してください。') || '').trim();
    if (email) {
      busy(true); say('ログインしています…');
      try { await exchange(auth, await signInWithEmailLink(auth, email, link)); }
      catch (e) { busy(false); say(explain(e), true); }
      finally { store.clear(); }
    }
  }

  $('#google').addEventListener('click', async () => {
    busy(true); say('Google の画面でログインしてください…');
    try { await exchange(auth, await signInWithPopup(auth, new GoogleAuthProvider())); }
    catch (e) { busy(false); say(explain(e), true); }
  });

  $('#email-form').addEventListener('submit', async ev => {
    ev.preventDefault();
    const email = $('#email').value.trim();
    busy(true);
    try {
      await sendSignInLinkToEmail(auth, email, {url: location.origin + loginUrl(), handleCodeInApp: true});
      store.set(email);
      say('ログイン用のリンクを送りました。このブラウザでメールのリンクを開いてください。');
    } catch (e) { say(explain(e), true); }
    busy(false);
  });
}

// ---------------------------------------------------------------- passkeys
// Works without Firebase: the Worker verifies passkeys itself.
const postJSON = async (path, body) => {
  const res = await fetch(path, {method: 'POST', credentials: 'same-origin', headers: {'content-type': 'application/json'}, body: JSON.stringify(body)});
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw Object.assign(new Error(data.error || 'うまくいきませんでした。'), {server: true});
  return data;
};
// Server messages are written for users; browser errors are mapped, never echoed.
function passkeyError(e) {
  const name = e?.cause?.name || e?.name;
  if (e?.server) return e.message;
  if (name === 'NotAllowedError' || name === 'AbortError') return '取りやめました。もう一度押すとやり直せます。';
  if (name === 'InvalidStateError') return 'この端末のパスキーは登録済みです。';
  return 'パスキーを使えませんでした。もう一度お試しください。';
}

function showRecovery(code) {
  $('#passkey-recovery').hidden = false;
  $('#recovery-code').textContent = code;
  $('#copy-recovery').onclick = () => navigator.clipboard?.writeText(code).then(() => say('コピーしました。'), () => {});
  $('#recovery-done').onclick = () => location.replace(NEXT);
}

function setupPasskeys() {
  if (!browserSupportsWebAuthn()) { $('#passkey').hidden = true; $('#passkey-login').hidden = true; return; }
  $('#passkey-login').addEventListener('click', async () => {
    busy(true); say('端末の画面でパスキーを選んでください…');
    try {
      const {challenge_id, options} = await postJSON('/api/auth/passkey/login/options', {});
      const response = await startAuthentication({optionsJSON: options});
      await postJSON('/api/auth/passkey/login/verify', {challenge_id, response});
      signedIn('ログインしました。');
    } catch (e) { busy(false); say(passkeyError(e), true); }
  });
  $('#passkey-signup').addEventListener('click', async () => {
    busy(true); say('端末の画面でパスキーを作ってください…');
    try {
      const {challenge_id, options} = await postJSON('/api/auth/passkey/register/options', {});
      const response = await startRegistration({optionsJSON: options});
      const data = await postJSON('/api/auth/passkey/register/verify', {challenge_id, response});
      busy(false);
      if (data.recovery_code) { $('#login').hidden = true; say('パスキーを作りました。下の復旧コードを控えてから進んでください。'); showRecovery(data.recovery_code); }
      else { say('パスキーを追加しました。'); location.replace(NEXT); }
    } catch (e) { busy(false); say(passkeyError(e), true); }
  });
}

// ---------------------------------------------------------------- account deletion
// D1 account APIs are called via /migration-api/: while ORIGINAL_UI_BRIDGE is on,
// other /api/* paths go to the old Render server.
function setupDelete() {
  if (!DELETE_MODE) return;
  document.title = 'アカウントの削除 ― たぐり';
  $('#delete-intro').hidden = false;
  $('#recovery-login').hidden = false;
  for (const id of ['#login-lead', '#passkey-signup', '#passkey-add-note', '#carry-over']) $(id).hidden = true;
  $('#recovery-login').addEventListener('submit', async ev => {
    ev.preventDefault();
    busy(true);
    try { await postJSON('/migration-api/recover', {code: $('#recovery-input').value}); signedIn(); }
    catch (e) { busy(false); say(e.server ? e.message : 'ログインできませんでした。', true); }
  });
  $('#delete-confirm').addEventListener('submit', async ev => {
    ev.preventDefault();
    busy(true); say('削除しています…');
    try {
      await postJSON('/migration-api/account/delete', {confirm: $('#delete-word').value, firebase_ready: !!firebaseUser});
    } catch (e) { busy(false); say(e.server ? e.message : '削除できませんでした。', true); return; }
    // Records are gone from taguri. Also remove the Google-side login record.
    let note = '';
    if (firebaseUser) {
      try { await deleteUser(firebaseUser); }
      catch { note = 'Google 側のログイン記録は消せませんでした。もう一度このページからログインして削除すると消えます。'; }
    }
    firebaseUser = null;
    $('#delete-confirm').hidden = true;
    $('#delete-done').hidden = false;
    say(note || 'アカウントとすべての記録を削除しました。', !!note);
  });
}

// Link mode: say what happens, and offer the recovery code / passkey sign-in
// that makes the session fresh enough to link (the server checks it).
function setupLink() {
  if (!LINK_MODE) return;
  document.title = 'Google・メールを結び付ける ― たぐり';
  $('#login-lead').textContent = 'いまのアカウントに Google かメールを結び付けます。10分以上前にログインした場合は、先に下の復旧コードかパスキーで本人確認をしてください。';
  for (const id of ['#about', '#passkey', '#carry-over']) { const el = $(id); if (el) el.hidden = true; }
  $('#recovery-login').hidden = false;
  $('#recovery-login').addEventListener('submit', async ev => {
    ev.preventDefault();
    busy(true);
    try { await postJSON('/migration-api/recover', {code: $('#recovery-input').value}); signedIn(); }
    catch (e) { busy(false); say(e.server ? e.message : 'ログインできませんでした。', true); }
  });
}

setupDelete();
setupLink();
setupPasskeys();
main().catch(e => say(explain(e), true));
