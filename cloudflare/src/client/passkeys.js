// Passkey management on the records page (/migration-data/). Bundled to
// public/vendor/passkeys.js by `npm run build:login`. Shown only when signed in.
import {startRegistration, browserSupportsWebAuthn} from '@simplewebauthn/browser';

const $ = s => document.querySelector(s);
const say = (text, bad = false) => { const s = $('#passkey-status'); s.textContent = text; s.classList.toggle('bad', bad); };
const day = t => t ? new Date(t * 1000).toLocaleDateString('ja-JP') : '未使用';
async function call(path, body) {
  const res = await fetch(path, body === undefined ? {credentials: 'same-origin'}
    : {method: 'POST', credentials: 'same-origin', headers: {'content-type': 'application/json'}, body: JSON.stringify(body)});
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw Object.assign(new Error(data.error || 'うまくいきませんでした。'), {status: res.status, server: true});
  return data;
}

async function refresh() {
  let data;
  try { data = await call('/api/auth/passkeys'); } catch { $('#passkeys').hidden = true; return; }
  $('#passkeys').hidden = false;
  const list = $('#passkey-list');
  list.replaceChildren(...data.passkeys.map((p, i) => {
    const li = document.createElement('li');
    // textContent only: nothing from the server is parsed as HTML
    li.textContent = `パスキー ${i + 1}（登録 ${day(p.created_at)}・最後に使用 ${day(p.last_used_at)}${p.synced ? '・同期あり' : ''}） `;
    const del = document.createElement('button');
    del.type = 'button'; del.textContent = '削除';
    del.onclick = async () => {
      if (!confirm('このパスキーを削除しますか？ その端末ではパスキーでログインできなくなります。')) return;
      try { await call('/api/auth/passkeys/delete', {id: p.id}); say('削除しました。'); refresh(); } catch (e) { say(e.message, true); }
    };
    li.append(del);
    return li;
  }));
  if (!data.passkeys.length) list.replaceChildren(Object.assign(document.createElement('li'), {textContent: 'まだ登録していません。'}));
}

$('#passkey-add')?.addEventListener('click', async ev => {
  const button = ev.currentTarget;
  button.disabled = true; say('端末の画面でパスキーを作ってください…');
  try {
    const {challenge_id, options} = await call('/api/auth/passkey/register/options', {});
    const response = await startRegistration({optionsJSON: options});
    await call('/api/auth/passkey/register/verify', {challenge_id, response});
    say('パスキーを追加しました。次からはパスキーでログインできます。');
    refresh();
  } catch (e) {
    const name = e?.cause?.name || e?.name;
    say(e.server ? e.message : name === 'NotAllowedError' || name === 'AbortError' ? '取りやめました。'
      : name === 'InvalidStateError' ? 'この端末のパスキーは登録済みです。' : 'パスキーを追加できませんでした。', true);
  }
  button.disabled = false;
});

if (browserSupportsWebAuthn()) {
  refresh();
  // The page shows the records area after sign-in without reloading; follow it.
  new MutationObserver(() => { if (!$('#content').hidden) refresh(); else $('#passkeys').hidden = true; })
    .observe($('#content'), {attributes: true, attributeFilter: ['hidden']});
}
