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
import {loginStore} from './login-store.js';

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
// 状態の文（「ログインを取りやめました」「リンクを送りました」など）は、押したボタン（欄）の直下に出す
// （起案者の指示 2026-10-18「『ログインを取りやめました』や『メールを送信した』的な文章は、対応する各ボタンの下に
// 文章が出るようにして。」）。#status は 1 つだけ（読み上げの aria-live もこの 1 つ）で、at の直後へ動かす。
// at を省くと今の場所のまま、null ならもとの場所（ログインの欄の上）に戻す。
// ボタンが横に並んでいるとき（パソコンの幅の .block.pair・.trio）は、並びを崩さないよう列の下に出す
const STATUS_HOME = $('#login');
const say = (text, bad = false, at) => {
  const s = $('#status');
  if (at === null) STATUS_HOME.before(s);
  else if (at) {
    const row = at.parentElement?.classList.contains('block') && getComputedStyle(at.parentElement).flexDirection === 'row';
    (row ? at.parentElement : at).after(s);
  }
  s.textContent = text; s.classList.toggle('bad', bad);
};
const busy = on => document.querySelectorAll('button, input').forEach(el => { el.disabled = on; });
// メールのリンク用の控え（アドレス・どちらの欄か・同意の版）。期限は login-store.js（#132）
const store = loginStore(() => localStorage);
// チェックが入っていれば、その版（login.html の value）。入っていなければ送らない
const agreed = () => ($('#agree')?.checked ? $('#agree').value : undefined);
// 同意が要ると言われたら、チェックの場所を目立たせる
const askAgree = e => { if (/同意して始める|利用規約/.test(e?.message || '')) { $('#agree-box')?.classList.add('need'); $('#agree')?.focus(); } };
// 新規登録の欄のボタン: チェックが無ければ、何も始めずにそう言う
const NEED_AGREE = 'はじめる前に利用規約とプライバシーポリシーを読んで、「同意して始める」にチェックを入れてください。';
function needAgree(at) {
  if (agreed()) return false;
  say(NEED_AGREE, true, at); askAgree({message: NEED_AGREE});
  return true;
}

async function exchange(auth, credential, intent, agree) {
  const idToken = await credential.user.getIdToken();
  const res = await fetch('/api/auth/firebase', {method: 'POST', credentials: 'same-origin',
    headers: {'content-type': 'application/json'}, body: JSON.stringify({id_token: idToken, link: LINK_MODE, intent, agree})});
  const data = await res.json().catch(() => ({}));
  // 前にアカウントを削除したとき、Google 側の記録を消せなかった（#128）。いまログインしたばかりなので消せる
  if (res.ok && data.firebase_delete_pending) return finishFirebaseDelete(auth, credential.user);
  if (DELETE_MODE) firebaseUser = credential.user;
  else await signOut(auth).catch(() => {});
  if (!res.ok) throw new Error(data.error || 'ログインできませんでした。');
  if (LINK_MODE) { say(data.linked ? '結び付けました。次からは Googleアカウントかメールでログインできます。' : 'すでに結び付いています。'); location.replace(NEXT === '/' ? '/account' : NEXT); return; }
  signedIn('ログインしました。');
}

// The server keeps only a hash of the Firebase UID for 30 days after the
// deletion and never takes this browser's word that it is gone (#128).
async function finishFirebaseDelete(auth, user) {
  busy(false);
  $('#delete-confirm').hidden = true;
  try {
    await deleteUser(user);
    say('前に削除したアカウントの、Google 側のログイン記録を消しました。これで削除は終わりです。新しく使うときは「新規登録」から始めてください。');
  } catch {
    await signOut(auth).catch(() => {});
    say('前に削除したアカウントの、Google 側のログイン記録を消せませんでした。少し待ってから、もう一度同じ方法でログインすると、また消します。', true);
  }
}

// After any sign-in: go to the records, or (delete mode) ask for confirmation.
function signedIn(message) {
  if (LINK_MODE) {
    busy(false);
    $('#recovery-login').hidden = true;
    say('本人確認ができました。続けて10分以内に、Googleアカウントかメールでログインすると結び付きます。', false, $('#login-lead'));
    return;
  }
  if (!DELETE_MODE) { say(message); location.replace(NEXT); return; }
  busy(false);
  for (const id of ['#login', '#signup', '#recovery-login']) $(id).hidden = true;
  $('#delete-confirm').hidden = false;
  say('本人確認ができました。10分以内に削除してください。', false, $('#delete-confirm > p'));
}

// Firebase error codes -> what the user can do about it. Never echo raw errors.
function explain(e) {
  const code = String(e?.code || '');
  if (code.includes('popup-closed') || code.includes('cancelled-popup')) return 'ログインを取りやめました。';
  if (code.includes('popup-blocked')) return 'ポップアップが止められました。ブラウザの設定で許可してから、もう一度押してください。';
  if (code.includes('invalid-email')) return 'メールアドレスを確認してください。';
  if (code.includes('invalid-action-code') || code.includes('expired-action-code')) return 'このリンクは使えません。もう一度メールを送ってください。';
  if (code.includes('too-many-requests') || code.includes('quota')) return '試した回数が多すぎます。しばらく待ってから試してください。';
  if (code.includes('network')) return '通信できませんでした。接続を確かめてください。';
  return e instanceof Error && !code ? e.message : 'ログインできませんでした。もう一度お試しください。';
}

async function main() {
  const res = await fetch('/api/auth/config', {credentials: 'omit'});
  if (!res.ok) { for (const id of ['#google', '#google-signup', '#email-signup']) $(id).disabled = true; $('#email-form').hidden = true; return; }
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
    if (!email && LINK_MODE) say('結び付けるには、メールを送ったときと同じブラウザでリンクを開いてください。', true, null);
    else if (!email) email = (prompt('確認のため、リンクを送ったメールアドレスを入力してください。') || '').trim();
    if (email) {
      const intent = store.intent();
      busy(true); say('ログインしています…', false, intent === 'signup' ? $('#email-signup') : $('#email-form label'));
      try { await exchange(auth, await signInWithEmailLink(auth, email, link), intent, intent === 'signup' ? store.agree() || agreed() : undefined); }
      catch (e) { busy(false); say(explain(e), true); askAgree(e); }
      finally { store.clear(); }
    }
  }

  const google = async (intent, agree, at) => {
    store.clear();   // 別の方法を始めたら、メールの控えは消す（#132）
    busy(true); say('Google の画面でログインしてください…', false, at);
    try { await exchange(auth, await signInWithPopup(auth, new GoogleAuthProvider()), intent, agree); }
    catch (e) { busy(false); say(explain(e), true); askAgree(e); }
  };
  $('#google').addEventListener('click', () => google('login', undefined, $('#google')));
  $('#google-signup').addEventListener('click', () => { if (!needAgree($('#google-signup'))) google('signup', agreed(), $('#google-signup')); });

  const sendLink = async (email, intent) => {
    // 文は、そのアドレスの欄（入力欄と「リンクを受け取る」）のすぐ下に出す
    const at = $(intent === 'signup' ? '#signup-email-form label' : '#email-form label');
    say('', false, at);
    busy(true);
    try {
      await sendSignInLinkToEmail(auth, email, {url: location.origin + loginUrl(), handleCodeInApp: true});
      store.set(email); store.setIntent(intent); store.setAgree(intent === 'signup' ? agreed() : undefined);
      say(`${intent === 'signup' ? '登録' : 'ログイン'}用のリンクを送りました。このブラウザで、1時間以内にメールのリンクを開いてください。`);
    } catch (e) { say(explain(e), true); }
    busy(false);
  };
  $('#email-form').addEventListener('submit', ev => { ev.preventDefault(); sendLink($('#email').value.trim(), 'login'); });
  // 「メールで始める」は、押すとアドレスの欄を出す（ふだんは畳んで、新規登録の欄を短く保つ）
  $('#email-signup').addEventListener('click', () => {
    if (needAgree($('#email-signup'))) return;
    say('', false, $('#email-signup'));
    $('#signup-email-form').hidden = false; $('#signup-email').focus();
  });
  $('#signup-email-form').addEventListener('submit', ev => {
    ev.preventDefault();
    if (!needAgree($('#signup-email-form label'))) sendLink($('#signup-email').value.trim(), 'signup');
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
  $('#copy-recovery').onclick = () => navigator.clipboard?.writeText(code).then(() => say('コピーしました。', false, $('#copy-recovery')), () => {});
  $('#recovery-done').onclick = () => location.replace(NEXT);
}

function setupPasskeys() {
  // パスキーを使えない画面（LINE・X などのアプリの中のブラウザに多い）では、ボタンを消すだけでなく、
  // ブラウザで開き直せば使えると書く（起案者の質問 2026-10-16「ログイン画面のパスキーのやつ消したの？」）
  if (!browserSupportsWebAuthn()) { $('#passkey-signup').hidden = true; $('#passkey-login').hidden = true; $('#passkey-none').hidden = false; return; }
  $('#passkey-login').addEventListener('click', async () => {
    store.clear();   // 別の方法を始めたら、メールの控えは消す（#132）
    busy(true); say('端末の画面でパスキーを選んでください…', false, $('#passkey-login'));
    try {
      const {challenge_id, options} = await postJSON('/api/auth/passkey/login/options', {});
      const response = await startAuthentication({optionsJSON: options});
      await postJSON('/api/auth/passkey/login/verify', {challenge_id, response});
      signedIn('ログインしました。');
    } catch (e) { busy(false); say(passkeyError(e), true); }
  });
  $('#passkey-signup').addEventListener('click', async () => {
    // パスキーで始めるのは、いつも新しいアカウント。端末に作らせる前に同意を確かめる
    if (needAgree($('#passkey-signup'))) return;
    const agree = agreed();
    store.clear();
    busy(true); say('端末の画面でパスキーを作ってください…', false, $('#passkey-signup'));
    try {
      const {challenge_id, options} = await postJSON('/api/auth/passkey/register/options', {agree});
      const response = await startRegistration({optionsJSON: options});
      const data = await postJSON('/api/auth/passkey/register/verify', {challenge_id, response, agree});
      busy(false);
      if (data.recovery_code) { $('#login').hidden = true; $('#signup').hidden = true; showRecovery(data.recovery_code); say('パスキーを作りました。下の復旧コードを控えてから進んでください。', false, $('#passkey-recovery > p')); }
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
  for (const id of ['#login-lead', '#signup']) $(id).hidden = true;
  $('#recovery-login').addEventListener('submit', async ev => {
    ev.preventDefault();
    say('', false, $('#recovery-login label'));
    busy(true);
    try { await postJSON('/migration-api/recover', {code: $('#recovery-input').value}); signedIn(); }
    catch (e) { busy(false); say(e.server ? e.message : 'ログインできませんでした。', true); }
  });
  $('#delete-confirm').addEventListener('submit', async ev => {
    ev.preventDefault();
    // 消す直前にもう一度確かめる（起案者の指示 2026-10-24「ポップアップで本当にいいですか？って確認してから消して」）
    if (!confirm('本当にアカウントを削除しますか？\n記録・評価・感想・お気に入り・ログインの情報がすべて消え、元に戻せません。')) {
      say('削除を取りやめました。', false, $('#delete-confirm button'));
      return;
    }
    busy(true); say('削除しています…', false, $('#delete-confirm button'));
    try {
      await postJSON('/migration-api/account/delete', {confirm: $('#delete-word').value, firebase_ready: !!firebaseUser});
    } catch (e) { busy(false); say(e.server ? e.message : '削除できませんでした。', true); return; }
    // Records are gone from taguri. Also remove the Google-side login record.
    let note = '';
    if (firebaseUser) {
      try { await deleteUser(firebaseUser); }
      catch { note = 'Google 側のログイン記録は消せませんでした。30日以内に、同じ Googleアカウント・メールでもう一度ログインすると消します（ログインの欄からで大丈夫です）。'; }
    }
    firebaseUser = null;
    $('#delete-confirm').hidden = true;
    $('#delete-done').hidden = false;
    say(note || 'アカウントとすべての記録を削除しました。', !!note, $('#delete-done h1'));
  });
}

// Link mode: say what happens, and offer the recovery code / passkey sign-in
// that makes the session fresh enough to link (the server checks it).
function setupLink() {
  if (!LINK_MODE) return;
  document.title = 'Googleアカウント・メールを結び付ける ― たぐり';
  $('#login-lead').textContent = 'いまのアカウントに Googleアカウントかメールを結び付けます。10分以上前にログインした場合は、先に下の復旧コードかパスキーで本人確認をしてください。';
  for (const id of ['#about', '#signup']) { const el = $(id); if (el) el.hidden = true; }
  $('#recovery-login').hidden = false;
  $('#recovery-login').addEventListener('submit', async ev => {
    ev.preventDefault();
    say('', false, $('#recovery-login label'));
    busy(true);
    try { await postJSON('/migration-api/recover', {code: $('#recovery-input').value}); signedIn(); }
    catch (e) { busy(false); say(e.server ? e.message : 'ログインできませんでした。', true); }
  });
}

// ふつうのログインでも復旧コードを使えるようにする。パスキーで始めた人には「パスキーを入れた端末をなくしたとき、
// このコードで記録に戻れます」と渡しているのに、入れる欄が削除と結び付けの画面（?purpose=delete・?link=1）にしか
// 無く、記録の画面（/migration-data/ の欄）もログインしないと開けなかった（#134 の通し検証）
function setupRecovery() {
  if (DELETE_MODE || LINK_MODE) return;
  $('#recovery-login').hidden = false;
  $('#recovery-login').addEventListener('submit', async ev => {
    ev.preventDefault();
    store.clear();   // 別の方法を始めたら、メールの控えは消す（#132）
    say('', false, $('#recovery-login label'));
    busy(true);
    try { await postJSON('/migration-api/recover', {code: $('#recovery-input').value.trim()}); signedIn('ログインしました。'); }
    catch (e) { busy(false); say(e.server ? e.message : 'ログインできませんでした。', true); }
  });
}

store.expire();
// チェックを入れたら、目立たせた枠を戻す
$('#agree')?.addEventListener('change', () => $('#agree-box')?.classList.remove('need'));
setupDelete();
setupLink();
setupRecovery();
setupPasskeys();
main().catch(e => say(explain(e), true, null));
