// アカウント: the signed-in user's own page (起案者の指示 2026-10-14「アカウントの
// ページを作成して（プロフィールページみたいなもの）」、見るのは本人だけ).
// A Worker-only screen: the Python service has no account page, so there is no
// parity test; it only reads the user's own rows and writes one setting.
import {E, ValueError} from './py.js';
import {loadWorks} from './works.js';
import {venueOf} from './row.js';

// The few icons this page uses (same paths as tools/taguri/icons.py and web/app.js ICON_P).
const ICONS = {
  user: 'M12 4a4 4 0 1 0 0 8 4 4 0 0 0 0-8zM4 20c0-3.3 3.6-5 8-5s8 1.7 8 5',
  book: 'M4 5h7v15H4zM13 5h7v15h-7M11 5v15',
  check: 'M4.5 12.5 9.5 18 20 6',
  info: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 11v5.5M12 7.6h.01',
};
const ico = (name, size = 16) => `<svg class="ico" viewBox="0 0 24 24" width="${size}" height="${size}"`
  + ` fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"`
  + ` aria-hidden="true"><path d="${ICONS[name]}"/></svg>`;
const h2 = (name, text) => `<h2>${ico(name, 18)}<span>${text}</span></h2>`;

const NAME_KEY = 'display_name';
// アイコン画像（起案者の指示 2026-10-14「アカウントのページでアイコン画像入れられるようにして」）。
// ブラウザが 160×160 に縮めて WebP（できなければ JPEG）にしたものを、本人の設定（app_setting）に
// data: URL のまま置く。上限 AVATAR_MAX 文字（約 45KB）×利用者 300 人でも 14MB で、D1 の
// 無料枠 5GB に響かない。中身の先頭を見て、WebP・JPEG・PNG の画像だけを受け付ける（SVG は受けない）。
const AVATAR_KEY = 'avatar';
const AVATAR_MAX = 60000;
const AVATAR_RE = /^data:image\/(webp|jpeg|png);base64,([A-Za-z0-9+/]+={0,2})$/;
function avatarOk(url) {
  const m = AVATAR_RE.exec(url);
  if (!m || url.length > AVATAR_MAX) return false;
  let head;
  try { head = atob(m[2].slice(0, 24)); } catch { return false; }
  const b = i => head.charCodeAt(i);
  if (m[1] === 'webp') return head.startsWith('RIFF') && head.slice(8, 12) === 'WEBP';
  if (m[1] === 'jpeg') return b(0) === 0xff && b(1) === 0xd8 && b(2) === 0xff;
  return b(0) === 0x89 && head.slice(1, 4) === 'PNG';
}
const NAME_MAX = 30;
const TOP = 5;

const jstDate = sec => {
  const d = new Date((sec + 9 * 3600) * 1000);
  return `${d.getUTCFullYear()}年${d.getUTCMonth() + 1}月${d.getUTCDate()}日`;
};

/** Most frequent values, ties in first-seen order. */
function top(values, n = TOP) {
  const count = new Map();
  for (const v of values) if (v) count.set(v, (count.get(v) || 0) + 1);
  return [...count].sort((a, b) => b[1] - a[1]).slice(0, n);
}

/** Groups of the stages the user's works are linked to (current catalogue, then past stages). */
async function groupsOf(ctx, sids) {
  const want = [...new Set(sids.filter(Boolean))], got = {};
  for (let i = 0; i < want.length; i += 90) {
    const part = want.slice(i, i + 90), qs = part.map(() => '?').join(',');
    const [cur, past] = await Promise.all([
      ctx.db.prepare(`SELECT stage_id, grp FROM rec_stage WHERE ver=(SELECT v FROM rec_meta WHERE k='current') AND stage_id IN (${qs})`).bind(...part).all(),
      ctx.db.prepare(`SELECT stage_id, grp FROM past_stage WHERE stage_id IN (${qs})`).bind(...part).all()]);
    for (const r of [...past.results, ...cur.results]) if (r.grp) got[r.stage_id] = r.grp;
  }
  return sids.map(s => got[s] || '');
}

const stat = (n, label, href) =>
  `<a class="acst" href="${href}?t=__TAGURI_TOKEN__"><b>${n}</b><span>${label}</span></a>`;
const ranked = (title, rows, unit) => rows.length
  ? `<div class="acrank"><h3>${title}</h3><ol>${rows.map(([v, n]) => `<li><span>${E(v)}</span><small>${n} ${unit}</small></li>`).join('')}</ol></div>`
  : '';

async function accountScreen(_params, ctx) {
  const db = ctx.db, uid = ctx.uid;
  const [u, name, avatar, passkeys, sessions, favs, reacts, works] = await Promise.all([
    db.prepare('SELECT created_at, firebase_uid, recovery_hash FROM users WHERE id=?').bind(uid).first(),
    db.prepare('SELECT value FROM app_setting WHERE user_id=? AND key=?').bind(uid, NAME_KEY).first(),
    db.prepare('SELECT value FROM app_setting WHERE user_id=? AND key=?').bind(uid, AVATAR_KEY).first(),
    db.prepare('SELECT count(*) AS n FROM passkeys WHERE user_id=?').bind(uid).first(),
    db.prepare('SELECT count(*) AS n FROM sessions WHERE user_id=? AND expires_at>?').bind(uid, Math.floor(ctx.now / 1000)).first(),
    db.prepare('SELECT count(*) AS n FROM favourites WHERE user_id=?').bind(uid).first(),
    db.prepare('SELECT count(*) AS n FROM reaction WHERE user_id=? AND interest=1').bind(uid).first(),
    loadWorks(ctx)]);
  const seen = works.filter(w => !w.unseen);
  const rated = seen.filter(w => w.verdict && w.verdict !== 'まだ判断できない');
  const noted = seen.filter(w => (w.note_impression || '').trim());
  const groups = top(await groupsOf(ctx, seen.map(w => w.stage_id || '')));
  const venues = top(seen.map(w => venueOf(w)));
  const display = name?.value || '';
  const google = Boolean(u?.firebase_uid);
  const recovery = Boolean(u?.recovery_hash) && !String(u.recovery_hash).startsWith('firebase:');
  const ways = [google ? 'Google またはメールのリンク' : '', passkeys.n ? `パスキー（${passkeys.n} 台）` : '', recovery ? '復旧コード' : '']
    .filter(Boolean).join('・') || '（なし）';
  const since = u?.created_at ? jstDate(u.created_at) : '';
  const body = `<h1>アカウント</h1>
<p class="lede">あなただけが見られるページです。ほかの人には表示されません。</p>
<section class="acct-card acct-me">
<div class="acav" aria-hidden="true">${avatar?.value && avatarOk(avatar.value) ? `<img src="${E(avatar.value)}" alt="">` : ico('user', 30)}</div>
<div class="acid"><p class="acname">${display ? E(display) : 'たぐりの利用者'}</p>
${since ? `<p class="acsince">${since}から使っています</p>` : ''}</div>
<div class="acpic"><label class="btn acpick">アイコン画像を選ぶ<input type="file" accept="image/*" data-account-avatar hidden></label>
<button type="button" data-account-avatar-clear${avatar?.value ? '' : ' hidden'}>画像を外す</button>
<span class="said" data-account-avatar-said role="status" aria-live="polite"></span>
<small>選んだ画像はまん中を正方形に切り抜いて、小さくしてから保存します。この画面にだけ出ます。</small></div>
<form class="acform" data-account-name>
<label for="acname">表示名<small>（${NAME_MAX} 文字まで。この画面にだけ出ます）</small></label>
<div class="acrow"><input id="acname" name="display_name" maxlength="${NAME_MAX}" value="${E(display)}" autocomplete="nickname">
<button type="submit">保存</button></div><p class="said" role="status" aria-live="polite"></p></form>
</section>
<section class="acct-card">${h2('book', 'これまでの記録')}
<div class="acstats">${stat(seen.length, '観た作品', '/records/works')}${stat(rated.length, '評価した作品', '/rate')}${stat(noted.length, '感想', '/rate/notes')}${stat(favs.n, 'お気に入り', '/recommend/favourites')}${stat(reacts?.n || 0, '興味あり', '/recommend/interest')}</div>
${groups.length || venues.length ? `<div class="acranks">${ranked('よく観ている団体', groups, '作品')}${ranked('よく行く劇場', venues, '作品')}</div>`
    : '<p class="note">観た公演を記録すると、よく観ている団体や劇場がここに出ます。</p>'}
</section>
<section class="acct-card">${h2('check', 'ログイン')}
<dl class="acdl"><dt>ログインの方法</dt><dd>${E(ways)}</dd>
<dt>ログイン中の端末</dt><dd>${sessions.n} 台</dd></dl>
<p class="acbtns"><a class="btn" href="/migration-data/#passkeys">パスキーを追加・削除する</a>
${google ? '' : '<a class="btn" href="/login?link=1&amp;next=%2Faccount">Google・メールを結び付ける</a>\n'}<button type="button" data-account-logout>この端末でログアウト</button>
<button type="button" data-account-logout="all">すべての端末でログアウト</button></p>
<p class="said" data-account-said role="status" aria-live="polite"></p>
</section>
<section class="acct-card acct-danger">${h2('info', 'アカウントの削除')}
<p>記録・評価・感想・お気に入り・ログインの情報をすべて消します。元に戻せません。</p>
<p><a href="/login?purpose=delete">アカウントを削除する</a></p>
</section>`;
  return {title: 'アカウント', body_html: body};
}

const putSetting = (ctx, key, value) => ctx.db.prepare('INSERT INTO app_setting(user_id,key,value,updated_at) VALUES(?,?,?,?) ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at')
  .bind(ctx.uid, key, value, new Date(ctx.now).toISOString()).run();

/** POST /api/account: {display_name} (empty clears it) or {avatar} (a small image as a data: URL; empty removes it). */
async function accountAction(input, ctx) {
  if (Object.hasOwn(input, 'avatar')) {
    const url = input.avatar;
    if (typeof url !== 'string') throw new ValueError('画像を確かめてください');
    if (!url) {
      await ctx.db.prepare('DELETE FROM app_setting WHERE user_id=? AND key=?').bind(ctx.uid, AVATAR_KEY).run();
      return {body: {ok: true, avatar: ''}};
    }
    if (!avatarOk(url)) throw new ValueError('この画像は使えません。使えるのは、小さくした WebP・JPEG・PNG の画像だけです。');
    await putSetting(ctx, AVATAR_KEY, url);
    return {body: {ok: true, avatar: url}};
  }
  const raw = input.display_name;
  if (typeof raw !== 'string') throw new ValueError('表示名を確かめてください');
  const name = raw.normalize('NFKC').replace(/[\u0000-\u001f\u007f]/g, '').trim();
  if (Array.from(name).length > NAME_MAX) throw new ValueError(`表示名は ${NAME_MAX} 文字までです`);
  if (name) {
    await putSetting(ctx, NAME_KEY, name);
  } else {
    await ctx.db.prepare('DELETE FROM app_setting WHERE user_id=? AND key=?').bind(ctx.uid, NAME_KEY).run();
  }
  return {body: {ok: true, display_name: name}};
}

export const accountScreens = {
  screens: {account: accountScreen},
  actions: {account: accountAction},
};
