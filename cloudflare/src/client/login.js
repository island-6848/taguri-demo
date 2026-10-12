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
  isSignInWithEmailLink, signInWithEmailLink, signOut,
} from 'firebase/auth';

const EMAIL_KEY = 'taguri_login_email';
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
    headers: {'content-type': 'application/json'}, body: JSON.stringify({id_token: idToken})});
  await signOut(auth).catch(() => {});
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'ログインできませんでした。');
  say(data.linked ? 'ログインしました。これまでの記録を引き継ぎました。' : 'ログインしました。');
  location.replace('/migration-data/');
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
  if (!res.ok) { say('ログインの準備ができていません。', true); busy(true); return; }
  const config = await res.json();
  const app = initializeApp({apiKey: config.apiKey, authDomain: config.authDomain, projectId: config.projectId});
  const auth = initializeAuth(app, {persistence: inMemoryPersistence, popupRedirectResolver: browserPopupRedirectResolver});
  auth.languageCode = 'ja';

  // Returning from the email link.
  const link = location.href;
  if (isSignInWithEmailLink(auth, link)) {
    history.replaceState(null, '', '/login');          // drop the one-time code from the address bar
    let email = store.get();
    // Opened on another device/browser: ask again instead of trusting the URL.
    if (!email) email = (prompt('確認のため、リンクを送ったメールアドレスを入力してください。') || '').trim();
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
      await sendSignInLinkToEmail(auth, email, {url: location.origin + '/login', handleCodeInApp: true});
      store.set(email);
      say('ログイン用のリンクを送りました。このブラウザでメールのリンクを開いてください。');
    } catch (e) { say(explain(e), true); }
    busy(false);
  });
}

main().catch(e => say(explain(e), true));
