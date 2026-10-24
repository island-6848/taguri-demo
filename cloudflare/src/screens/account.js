import {SESSION_TTL} from '../session-policy.js';
// アカウント: the signed-in user's own page (起案者の指示 2026-10-14「アカウントの
// ページを作成して（プロフィールページみたいなもの）」、見るのは本人だけ).
// A Worker-only screen: the Python service has no account page, so there is no
// parity test; it only reads the user's own rows and writes one setting.
import {E, ValueError} from './py.js';
import {loadWorks, titleKey} from './works.js';
import {venueOf} from './row.js';
import {loadDeclared, KINDS} from './lists.js';

// The few icons this page uses (same paths as tools/taguri/icons.py and web/app.js ICON_P).
const ICONS = {
  user: 'M12 4a4 4 0 1 0 0 8 4 4 0 0 0 0-8zM4 20c0-3.3 3.6-5 8-5s8 1.7 8 5',
  book: 'M4 5h7v15H4zM13 5h7v15h-7M11 5v15',
  check: 'M4.5 12.5 9.5 18 20 6',
  info: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 11v5.5M12 7.6h.01',
  pencil: 'M4 20h4L18 10l-4-4L4 16zM13.5 6.5l4 4',
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

/**
 * 多い順の上位 n 件 [[名前, 数, 順位]...]。counts: Map(名前 -> 数)。同じ数は同じ順位（1, 2, 2, 4）で、名前の順に並べる。
 * 同じ数が n 件目をまたぐときも、その数の分はすべて出す（同じ順位なのに出る・出ないが分かれないように）
 */
export function ranking(counts, n = TOP) {
  const rows = [...counts].filter(([v, c]) => v && c > 0).sort((a, b) => (b[1] - a[1]) || a[0].localeCompare(b[0], 'ja'));
  const cut = rows.length > n ? rows[n - 1][1] : 0;
  return rows.filter(([, c], i) => i < n || c === cut).map(([v, c]) => [v, c, 1 + rows.filter(r => r[1] > c).length]);
}
/** 名前ごとの、違う作品（題名の鍵）の数 */
export function worksBy(pairs) {
  const sets = new Map();
  for (const [name, key] of pairs) if (name && key) { if (!sets.has(name)) sets.set(name, new Set()); sets.get(name).add(key); }
  return new Map([...sets].map(([name, keys]) => [name, keys.size]));
}

/** Groups of the stages the user's works are linked to (current catalogue, then past stages). */
export async function groupsOf(ctx, sids) {
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
/**
 * ランキングの一覧（起案者の指示 2026-10-20「よく観る団体とよく観る劇場、それぞれランキングぽいデザインに」）。
 * 順位の札（1〜3 位は色つき）・名前・1 位を満たんにした棒・数。rows は ranking() の行
 */
export const rankList = (rows, unit, cls = '') => {
  const max = rows.length ? rows[0][1] : 1;
  return `<ol class="rk${cls ? ' ' + cls : ''}">${rows.map(([v, n, r]) => `<li class="rk-${r <= 3 ? r : 'n'}">`
    + `<b class="rk-no" aria-label="${r} 位">${r}</b><span class="rk-name">${E(v)}</span>`
    + `<span class="rk-bar" aria-hidden="true"><i style="width:${Math.max(4, Math.round(100 * n / max))}%"></i></span>`
    + `<small>${n} ${unit}</small></li>`).join('')}</ol>`;
};
const ranked = (title, rows, unit) => rows.length ? `<div class="acrank"><h3>${title}</h3>${rankList(rows, unit)}</div>` : '';
/**
 * よく行く劇場: 作品数（同じ作品は 1）と、行った回数（同じ作品でも観た回ごと。上の「観た回数」と同じ数え方）を切り替える
 * （起案者の指示 2026-10-20）。切り替えは押し口（radio）と CSS だけで、画面のスクリプトに頼らない
 */
const venueRanks = (byWorks, byVisits) => (byWorks.length
  ? `<div class="acrank acrank-v"><h3>よく行く劇場</h3>
<div class="rk-mode" role="radiogroup" aria-label="劇場の数え方">
<input type="radio" name="rk-venue" id="rk-v-works" value="works" checked><label for="rk-v-works">作品数</label>
<input type="radio" name="rk-venue" id="rk-v-visits" value="visits"><label for="rk-v-visits">行った回数</label></div>
${rankList(byWorks, '作品', 'rk-works')}${rankList(byVisits, '回', 'rk-visits')}</div>`
  : '');

async function accountScreen(_params, ctx) {
  const db = ctx.db, uid = ctx.uid;
  const [u, name, avatar, passkeys, sessions, favs, reacts, works] = await Promise.all([
    db.prepare('SELECT created_at, firebase_uid, recovery_hash FROM users WHERE id=?').bind(uid).first(),
    db.prepare('SELECT value FROM app_setting WHERE user_id=? AND key=?').bind(uid, NAME_KEY).first(),
    db.prepare('SELECT value FROM app_setting WHERE user_id=? AND key=?').bind(uid, AVATAR_KEY).first(),
    db.prepare('SELECT count(*) AS n FROM passkeys WHERE user_id=?').bind(uid).first(),
    db.prepare('SELECT count(*) AS n FROM sessions WHERE user_id=? AND expires_at>? AND created_at>?').bind(uid, Math.floor(ctx.now / 1000), Math.floor(ctx.now / 1000) - SESSION_TTL).first(),
    // お気に入りは、いまは本人の設定（app_setting の declared、lists.loadDeclared）に入る。前は古い表（favourites）だけを
    // 数えていて、いつも 0 件だった（起案者の指摘 2026-10-18「『お気に入り』が常に0件なのなぜ？」）
    loadDeclared(ctx),
    db.prepare('SELECT count(*) AS n FROM reaction WHERE user_id=? AND interest=1').bind(uid).first(),
    loadWorks(ctx)]);
  const seen = works.filter(w => !w.unseen);
  // 観た回数: 作品でまとめず、劇場に行った回数（同じ作品を 2 回観たら 2。記録の times と、まとめた別の回の記録 merged）。起案者の指示 2026-10-18
  const rated = seen.filter(w => w.verdict && w.verdict !== 'まだ判断できない');
  const noted = seen.filter(w => (w.note_impression || '').trim());
  // 団体・劇場は、違う作品（題名の鍵）の数で並べる。前は記録の数で、同じ作品を別の日に観ると 2 作品になっていた
  const grps = await groupsOf(ctx, seen.map(w => w.stage_id || ''));
  const groups = ranking(worksBy(seen.map((w, i) => [grps[i], titleKey(w.title)])));
  const venueWorks = ranking(worksBy(seen.map(w => [venueOf(w), titleKey(w.title)])));
  const visits = new Map();
  for (const w of seen) { const v = venueOf(w); if (v) visits.set(v, (visits.get(v) || 0) + (Number(w.times) || 1) + (w.merged || []).length); }
  const venueVisits = ranking(visits);
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
<div class="acid"><p class="acname"><span class="acname-t">${display ? E(display) : 'たぐりの利用者'}</span><button type="button" class="acedit" data-account-name-edit aria-label="表示名を変える" title="表示名を変える">${ico('pencil', 16)}</button></p>
${since ? `<p class="acsince">${since}から使っています</p>` : ''}</div>
<div class="acpic"><label class="btn acpick">アイコン画像を選ぶ<input type="file" accept="image/*" data-account-avatar hidden></label>
<button type="button" data-account-avatar-clear${avatar?.value ? '' : ' hidden'}>画像を外す</button>
<span class="said" data-account-avatar-said role="status" aria-live="polite"></span>
<small>選んだ画像はまん中を正方形に切り抜いて、小さくしてから保存します。この画面にだけ出ます。</small></div>
<!-- 表示名は名前の右のえんぴつを押して直す（起案者の指示 2026-10-19「表示名の編集は、名前の右にえんぴつアイコンおいて編集できるようにして」） -->
<form class="acform" data-account-name hidden>
<label for="acname">表示名<small>（${NAME_MAX} 文字まで。この画面にだけ出ます）</small></label>
<div class="acrow"><input id="acname" name="display_name" maxlength="${NAME_MAX}" value="${E(display)}" autocomplete="nickname">
<button type="submit">保存</button><button type="button" data-account-name-cancel>やめる</button></div><p class="said" role="status" aria-live="polite"></p></form>
</section>
<section class="acct-card">${h2('book', 'これまでの記録')}
<div class="acstats">${stat(seen.length, '観た作品', '/records/works')}${stat(seen.reduce((n, w) => n + (Number(w.times) || 1) + (w.merged || []).length, 0), '観た回数', '/records/works')}${stat(rated.length, '評価した作品', '/rate')}${stat(noted.length, '感想', '/rate/notes')}${stat(KINDS.reduce((n, k) => n + (favs[k] || []).length, 0), 'お気に入り', '/recommend/favourites')}${stat(reacts?.n || 0, '興味あり', '/recommend/interest')}</div>
${groups.length || venueWorks.length ? `<div class="acranks">${ranked('よく観ている団体', groups, '作品')}${venueRanks(venueWorks, venueVisits)}</div>`
    : '<p class="note">観た公演を記録すると、よく観ている団体や劇場がここに出ます。</p>'}
</section>
<section class="acct-card">${h2('check', 'ログイン')}
<dl class="acdl"><dt>ログインの方法</dt><dd>${E(ways)}</dd>
<dt>ログイン中の端末</dt><dd>${sessions.n} 台</dd></dl>
<p class="acbtns"><a class="btn" href="/migration-data/#passkeys">パスキーを追加・削除する</a>
${google ? '' : '<a class="btn" href="/login?link=1&amp;next=%2Faccount">Google・メールを結び付ける</a>\n'}${recovery ? '<a class="btn" href="/migration-data/#recovery-reissue">復旧コードを作り直す</a>\n' : ''}<button type="button" data-account-logout>この端末でログアウト</button>
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
