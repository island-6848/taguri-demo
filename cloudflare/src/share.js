// 共有リンク（起案者の指示 2026-10-21「共有できるようにしたい。公演単体か、または指定のページをパブリックで公開するか選べるように」、
// dec-share-links）。本人が作った /s/<token> は、リンクを知る人ならログインなしで読める。検索エンジンには載せない（noindex）。
//
// - 共有できるもの: 公演 1 件のカード（「チケットを購入しました！」など）・観劇記録の一覧・眺める・お気に入り・観劇史年表
// - 評価・感想・表示名とアイコンは、共有するときに本人が選ぶ（既定はどれも出さない）
// - 公開ページは、毎回いまの記録から作る。ログインした人の画面（screens/）は使い回さない。
//   画面には書き換えの操作や内部の道（/records/... など）があり、出すものを 1 つずつ選んだほうが漏れが無いため。
//   記録を読むのも、読むだけの問い合わせにする（works.loadWorks は取り消した記録を消すなど、書き込みを伴う）
// - 本人の user_id・記録の鍵（work_key）・内部の道は、公開ページに出さない
import {E, localNow, strip, ValueError} from './screens/py.js';
import {titleKey} from './screens/works.js';
import {venueOf} from './screens/row.js';
import {loadDeclared, KINDS as FAV_KINDS} from './screens/lists.js';
import {ranking, worksBy, groupsOf, rankList} from './screens/account.js';
import {ratedRows} from './screens/records.js';
import {spiralPanel} from './screens/charts.js';
import {timetableFor} from './screens/timetable.js';
import {conquestFor} from './screens/conquest.js';
import {panel as chroniclePanel} from './screens/chronicle.js';
import {r2ReadAllowed} from './free-tier.js';

export const SHARE_KINDS = {stage: '公演', works: '観劇記録の一覧', records: '眺める', favourites: 'お気に入り', chronicle: '観劇史年表'};
export const STAGE_LABELS = {owned: 'この公演のチケットを購入しました！', interest: 'この公演を「興味あり」にしました！', watched: 'この公演を観ました！'};
export const SHARE_MAX = 100;               // 1 人の共有リンクの上限（migrations/0044 のトリガーと同じ）
const WORKS_MAX = 1000;                      // 一覧に出す記録の上限
const TOKEN_RE = /^[A-Za-z0-9_-]{22}$/;
// 公開ページは短く控える（同じリンクが多く開かれても D1 を毎回読まない）。取り消しの反映は最長この秒数遅れる
const PUBLIC_MAX_AGE = 60;

/** 推測できない 22 文字（128 ビット、base64url） */
export function newToken(random = n => crypto.getRandomValues(new Uint8Array(n))) {
  return btoa(String.fromCharCode(...random(16))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
const flag = v => (v === true || v === 1 || v === '1' || v === 'true' ? 1 : 0);

/** 公演の表（これからの公演 rec_stage、無ければ過去の公演 past_stage）から、出してよい項目だけ */
async function stageInfo(db, sid) {
  const cur = await db.prepare("SELECT title, start, end, entry FROM rec_stage WHERE ver=(SELECT v FROM rec_meta WHERE k='current') AND stage_id=?")
    .bind(sid).first().catch(() => null);
  if (cur) {
    let e = {};
    try { e = JSON.parse(cur.entry || '{}') || {}; } catch { /* broken row */ }
    return {title: cur.title || e.title || '', start: cur.start || '', end: cur.end || '', venue: e.theater || e.venue || '',
      group: e.group || '', pref: e.pref || '', url: /^https:\/\//.test(e.url || '') ? e.url : ''};
  }
  const past = await db.prepare('SELECT title, start, end, venue, grp, pref FROM past_stage WHERE stage_id=?').bind(sid).first().catch(() => null);
  if (!past) return null;
  return {title: past.title || '', start: past.start || '', end: past.end || '', venue: past.venue || '', group: past.grp || '',
    pref: past.pref || '', url: /^\d+$/.test(sid) ? `https://stage.corich.jp/stage/${sid}` : ''};
}

// ---------------------------------------------------------------- 作る・一覧・取り消す（/api/share、本人だけ）
async function createShare(b, ctx) {
  const kind = String(b.kind ?? '');
  if (!Object.hasOwn(SHARE_KINDS, kind)) throw new ValueError('共有するものの種類がおかしい');
  let target = '', label = '';
  if (kind === 'stage') {
    target = String(b.stage_id ?? '').trim().slice(0, 40);
    label = String(b.label ?? '');
    // 日記帳の行（観ました）は記録の鍵で来る。結び付いた公演を引く（日記帳の HTML は Python 版と同じ形のままにするため、押し口は app.js が足す）
    if (!target && label === 'watched' && b.work_key) {
      target = (await ctx.db.prepare('SELECT stage_id FROM works WHERE user_id=? AND work_key=?').bind(ctx.uid, String(b.work_key).slice(0, 200)).first())?.stage_id || '';
      if (!target) throw new ValueError('この記録は、まだ公演に結び付いていません。「公演詳細を直す」から公演を選ぶと、公演のカードとして共有できます');
    }
    if (!target || !Object.hasOwn(STAGE_LABELS, label)) throw new ValueError('公演と、カードの見出し（購入・興味あり・観た）が要る');
    if (!(await stageInfo(ctx.db, target))) throw new ValueError('この公演は手元の公演一覧に見当たりません');
  }
  const n = (await ctx.db.prepare('SELECT count(*) AS n FROM share WHERE user_id=?').bind(ctx.uid).first())?.n || 0;
  if (n >= SHARE_MAX) throw new ValueError(`共有リンクは ${SHARE_MAX} 件までです。設定の「共有中のリンク」から、使わないものを取り消してください`);
  const token = newToken();
  await ctx.db.prepare('INSERT INTO share(token,user_id,kind,target,label,show_verdict,show_note,show_name,created_at) VALUES(?,?,?,?,?,?,?,?,?)')
    .bind(token, ctx.uid, kind, target, label, flag(b.verdict), flag(b.note), flag(b.name), new Date(ctx.now ?? Date.now()).toISOString()).run();
  return {body: {ok: true, token, path: `/s/${token}`,
    said: 'リンクを作りました。このリンクを知っている人は、ログインしなくても見られます（検索エンジンには載りません）'}};
}

export async function listShares(ctx) {
  const {results} = await ctx.db.prepare('SELECT token, kind, target, label, show_verdict, show_note, show_name, created_at FROM share WHERE user_id=? AND revoked_at IS NULL ORDER BY created_at DESC')
    .bind(ctx.uid).all();
  const out = [];
  for (const r of results) {
    const what = r.kind === 'stage' ? `${(await stageInfo(ctx.db, r.target))?.title || '（公演が見つかりません）'}（${STAGE_LABELS[r.label] || ''}）` : SHARE_KINDS[r.kind] || r.kind;
    out.push({token: r.token, path: `/s/${r.token}`, kind: r.kind, what, verdict: !!r.show_verdict, note: !!r.show_note, name: !!r.show_name,
      created_at: r.created_at});
  }
  return out;
}

async function revokeShare(b, ctx) {
  const token = String(b.token ?? '');
  if (!TOKEN_RE.test(token)) throw new ValueError('取り消すリンクがおかしい');
  const r = await ctx.db.prepare('DELETE FROM share WHERE token=? AND user_id=?').bind(token, ctx.uid).run();
  if (!(r.meta?.changes ?? r.changes)) throw new ValueError('このリンクは見つかりません（もう取り消したかもしれません）');
  // この場所の控えも消す（ほかの場所の控えは PUBLIC_MAX_AGE 秒で切れる）
  try { if (typeof caches !== 'undefined' && ctx.origin) await caches.default.delete(`${ctx.origin}/s/${token}`); } catch { /* 控えが無ければ何もしない */ }
  return {body: {ok: true, said: 'リンクを取り消しました。このリンクはもう開けません'}};
}

async function shareAction(b, ctx) {
  const action = String(b.action ?? '');
  if (action === 'create') return createShare(b, ctx);
  if (action === 'revoke') return revokeShare(b, ctx);
  if (action === 'list') return {body: {ok: true, shares: await listShares(ctx)}};
  throw new ValueError('action（create / revoke / list）が要る');
}

export const shareScreens = {screens: {}, actions: {share: shareAction}};

// 共有の押し口（app.js の data-share-kind が、選ぶ欄の小窓を開く）。字は出さず、小さい共有の印だけ（起案者の指示 2026-10-21）。小窓で評価・感想・名前を選んでからリンクを作る
const SHARE_ICON = '<svg class="ico" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.7" '
  + 'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 15V4M8 8l4-4 4 4M5 13v6h14v-6"/></svg>';
/** 公演 1 件のカードの共有（label: owned 購入済・interest 興味あり・watched 観た） */
export const shareStageButton = (sid, label) => `<button type="button" class="share-open" data-share-kind="stage" data-share-stage="${E(sid)}"`
  + ` data-share-label="${E(label)}" aria-label="この公演を共有" title="共有">${SHARE_ICON}</button>`;
/** ページの共有（kind: works・records・favourites・chronicle）。見出しの右に小さい印だけを置く（起案者の指示 2026-10-21「小さめの共有アイコンでよい」） */
export const sharePageButton = kind => `<button type="button" class="share-open share-page-btn" data-share-kind="${E(kind)}" aria-label="このページを共有" title="このページを共有">${SHARE_ICON}</button>`;
/** カード・行の終わり（</article>）の手前に押し口を足す */
export const withShareButton = (html, button) => html.replace(/<\/article>(\s*)$/, `${button}</article>$1`);

/** 設定の画面の「共有中のリンク」（screens/settings.js から呼ぶ）。取り消しは app.js の data-share-revoke */
export async function sharesCardHtml(ctx) {
  let rows = [];
  try { rows = await listShares(ctx); } catch { return ''; }
  const items = rows.map(r => `<li><a href="${E(r.path)}" target="_blank" rel="noopener">${E(r.what)}</a>`
    + `<small>${[r.verdict && '評価', r.note && '感想', r.name && '名前'].filter(Boolean).map(E).join('・') || '記録の中身なし'}・${E(String(r.created_at).slice(0, 10))}</small>`
    + `<button type="button" class="share-copy" data-share-copy="${E(r.path)}">リンクをコピー</button>`
    + `<button type="button" data-share-revoke="${E(r.token)}">取り消す</button><span class="said"></span></li>`).join('');
  return `<details class="card" id="shares"><summary><h2><span>共有中のリンク（${rows.length} 件）</span></h2></summary>
<p class="lead">リンクを知っている人は、ログインしなくても見られます（検索エンジンには載りません）。取り消すと、そのリンクはすぐ開けなくなります。</p>
${rows.length ? `<ul class="share-list">${items}</ul>` : '<p class="empty">共有しているリンクはありません。公演のカードや、観劇記録・眺める・お気に入り・年表の画面の「共有」から作れます。</p>'}
</details>`;
}

// ---------------------------------------------------------------- 公開ページ（/s/<token>、ログインなし）
/** 本人の記録を読むだけで集める（works.loadWorks と同じ見分け方。取り消した・まとめた記録は外す。書き込みはしない） */
export async function publicWorks(db, uid) {
  const [works, excluded, merges] = await Promise.all([
    db.prepare('SELECT work_key, title, first_date, last_date, times, verdict, note_impression, venue, time, stage_id FROM works WHERE user_id=? ORDER BY work_key').bind(uid).all(),
    db.prepare('SELECT uid FROM excluded WHERE user_id=?').bind(uid).all(),
    db.prepare('SELECT work_key FROM merges WHERE user_id=?').bind(uid).all()]);
  const dropped = new Set(excluded.results.filter(r => r.uid.startsWith('work:') || r.uid.startsWith('purged:')).map(r => r.uid.slice(r.uid.indexOf(':') + 1)));
  const merged = new Set(merges.results.map(r => r.work_key));
  return works.results.filter(w => !dropped.has(w.work_key) && !merged.has(w.work_key))
    .map(w => ({work_key: w.work_key, title: w.title || '', first_date: w.first_date || '', last_date: w.last_date || '', times: w.times || 1,
      verdict: w.verdict || '', note_impression: w.note_impression || '', venue: w.venue || '', time: w.time || '', stage_id: w.stage_id || '',
      unseen: false, shows: [], hand: {}, merged: [], pieces: [], aspects: ''}))
    .sort((a, b) => (b.last_date || '0000').localeCompare(a.last_date || '0000'));
}

/** 共有の設定に合わせて、出さないもの（評価・感想）を消した記録 */
export const shown = (ws, s) => ws.map(w => ({...w, verdict: s.show_verdict ? w.verdict : '', note_impression: s.show_note ? w.note_impression : ''}));

/** 画面の部品（眺める・年表）から、内部の道・操作・スクリプトを外す */
export function publicHtml(html) {
  return String(html || '')
    .replace(/<script\b[\s\S]*?<\/script>/gi, '')
    .replace(/<(button|form|select|textarea)\b[\s\S]*?<\/\1>/gi, '')
    .replace(/<input\b[^>]*>/gi, '')
    .replace(/<a\b[^>]*\bhref="(?!https:\/\/)[^"]*"[^>]*>([\s\S]*?)<\/a>/gi, '<span>$1</span>')
    .replace(/\s(data-[a-z0-9-]+)="[^"]*"/gi, '')
    .replace(/__TAGURI_TOKEN__/g, '');
}

const page = ({title, card, body, origin, path, name}) => `<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow,noarchive">
<title>${E(title)}</title>
<meta property="og:type" content="article"><meta property="og:site_name" content="たぐり">
<meta property="og:title" content="${E(card.title)}"><meta property="og:description" content="${E(card.description)}">
<meta property="og:url" content="${E(origin + path)}"><meta property="og:image" content="${E(origin + (card.image || '/assets/og.png'))}">
<meta name="twitter:card" content="${card.image ? 'summary' : 'summary_large_image'}"><meta name="twitter:title" content="${E(card.title)}">
<meta name="twitter:description" content="${E(card.description)}"><meta name="twitter:image" content="${E(origin + (card.image || '/assets/og.png'))}">
<link rel="stylesheet" href="/style.css"><link rel="stylesheet" href="/theme.css"><link rel="stylesheet" href="/fonts.css">
</head><body class="share-page"><main id="content" class="share-main">
<header class="share-head"><span class="share-brand">たぐり</span>${name ? `<span class="share-who">${name}</span>` : ''}</header>
${body}
<footer class="share-pfoot"><p>たぐりの利用者が、自分の観劇の記録から共有したページです。</p>
<p><a href="/login">たぐりで観劇を記録する</a></p></footer>
</main></body></html>`;

function notFound() {
  const html = `<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><title>たぐり</title><link rel="stylesheet" href="/style.css"><link rel="stylesheet" href="/theme.css"></head>
<body class="share-page"><main class="share-main"><header class="share-head"><span class="share-brand">たぐり</span></header>
<p>このリンクは取り消されたか、ありません。</p><p><a href="/login">たぐりで観劇を記録する</a></p></main></body></html>`;
  return new Response(html, {status: 404, headers: publicHeaders(0)});
}

function publicHeaders(maxAge = PUBLIC_MAX_AGE) {
  return {'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': maxAge ? `public, max-age=${maxAge}` : 'no-store',
    'X-Robots-Tag': 'noindex, nofollow, noarchive', 'Referrer-Policy': 'no-referrer', 'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'Content-Security-Policy': "default-src 'self'; script-src 'none'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"};
}

async function whoHtml(db, uid, s) {
  if (!s.show_name) return '';
  const [n, a] = await Promise.all([
    db.prepare("SELECT value FROM app_setting WHERE user_id=? AND key='display_name'").bind(uid).first(),
    db.prepare("SELECT value FROM app_setting WHERE user_id=? AND key='avatar'").bind(uid).first()]);
  const name = strip(n?.value || '');
  const avatar = /^data:image\/(webp|jpeg|png);base64,[A-Za-z0-9+/]+={0,2}$/.test(a?.value || '') ? a.value : '';
  if (!name && !avatar) return '';
  return `${avatar ? `<img class="share-avatar" src="${E(avatar)}" alt="" width="28" height="28">` : ''}${name ? `<b>${E(name)}</b> さんの共有` : ''}`;
}

const period = (a, b) => (a && b && a !== b ? `${a.replace(/-/g, '/')} 〜 ${b.replace(/-/g, '/')}` : (a || b || '').replace(/-/g, '/'));
const recordLine = w => `<li><span class="share-date">${E((w.first_date || '').replace(/-/g, '/'))}</span>`
  + `<b class="share-title">${E(w.title)}</b>${venueOf(w) ? `<span class="share-venue">${E(venueOf(w))}</span>` : ''}`
  + (w.verdict ? `<span class="share-verdict">${E(w.verdict)}</span>` : '')
  + (strip(w.note_impression) ? `<p class="share-note">${E(w.note_impression).replace(/\n/g, '<br>')}</p>` : '') + '</li>';

async function stageBody(db, uid, s, poster) {
  const st = await stageInfo(db, s.target);
  if (!st) return null;
  let mine = '';
  if (s.label === 'watched' && (s.show_verdict || s.show_note)) {
    const w = (await publicWorks(db, uid)).find(x => x.stage_id === s.target);
    if (w) {
      const v = s.show_verdict && w.verdict ? `<p class="share-verdict-big">評価 <b>${E(w.verdict)}</b></p>` : '';
      const n = s.show_note && strip(w.note_impression) ? `<blockquote class="share-note">${E(w.note_impression).replace(/\n/g, '<br>')}</blockquote>` : '';
      mine = v + n;
    }
  }
  const head = STAGE_LABELS[s.label] || '';
  return {title: `${head} ${st.title}`, card: {title: `${head}『${st.title}』`, description: [period(st.start, st.end), st.venue].filter(Boolean).join('・') || 'たぐりで共有された公演',
    image: poster ? `/s/${s.token}/poster` : ''},
  body: `<article class="card share-stage">
<p class="share-label">${E(head)}</p>
${poster ? `<img class="share-poster" src="/s/${E(s.token)}/poster" alt="">` : ''}
<h1>${E(st.title)}</h1>
<p class="share-meta">${E(period(st.start, st.end))}${st.venue ? `<br>${E(st.venue)}${st.pref ? `（${E(st.pref)}）` : ''}` : ''}${st.group ? `<br>${E(st.group)}` : ''}</p>
${mine}
${st.url ? `<p><a href="${E(st.url)}" rel="noopener nofollow" target="_blank">公演のページ（CoRich）を見る</a></p>` : ''}
</article>`};
}

async function worksBody(ws) {
  if (!ws.length) return '<p class="empty">まだ記録がありません。</p>';
  const years = new Map();
  for (const w of ws.slice(0, WORKS_MAX)) {
    const y = (w.first_date || '').slice(0, 4) || '日付なし';
    if (!years.has(y)) years.set(y, []);
    years.get(y).push(w);
  }
  return [...years].map(([y, rows]) => `<section class="card share-year"><h2>${E(y)}<small>${rows.length} 本</small></h2>`
    + `<ol class="share-records">${rows.map(recordLine).join('')}</ol></section>`).join('');
}

async function recordsBody(db, uid, ws, today) {
  const ctx = {db, uid, today, now: Date.now()};
  const parts = [];
  const groups = ranking(worksBy((await groupsOf(ctx, ws.map(w => w.stage_id || ''))).map((g, i) => [g, titleKey(ws[i].title)])));
  const venues = ranking(worksBy(ws.map(w => [venueOf(w), titleKey(w.title)])));
  if (groups.length || venues.length) {
    parts.push(`<section class="card"><h2>よく観る団体・よく行く劇場</h2>
${groups.length ? `<div class="acrank"><h3>よく観る団体</h3>${rankList(groups, '作品')}</div>` : ''}
${venues.length ? `<div class="acrank"><h3>よく行く劇場</h3>${rankList(venues, '作品')}</div>` : ''}</section>`);
  }
  for (const make of [() => spiralPanel(ws), () => timetableFor(ctx, ws, today), () => conquestFor(ctx, ws)]) {
    try { parts.push(publicHtml(await make())); } catch { /* 図が描けなくてもほかは出す */ }
  }
  return parts.join('\n');
}

async function favouritesBody(db, uid) {
  const dec = await loadDeclared({db, uid});
  const rows = FAV_KINDS.filter(k => (dec[k] || []).length);
  if (!rows.length) return '<p class="empty">お気に入りはまだありません。</p>';
  return `<section class="card share-favs">${rows.map(k => `<h2>${E(k)}</h2><ul class="share-tags">${dec[k].map(n => `<li>${E(n)}</li>`).join('')}</ul>`).join('')}</section>`;
}

async function chronicleBody(db, uid, ws, s) {
  const ctx = {db, uid};
  const rated = s.show_verdict ? await ratedRows(ctx, ws) : [];
  const html = publicHtml(chroniclePanel(ws, rated));
  return html || '<p class="empty">まだ年表を描けるだけの記録がありません。</p>';
}

/** GET /s/<token>（と /s/<token>/poster）。共有リンクでなければ null */
export async function publicShare(request, env, url) {
  const m = /^\/s\/([A-Za-z0-9_-]{22})(\/poster)?$/.exec(url.pathname);
  if (!m) return null;
  if (request.method !== 'GET' && request.method !== 'HEAD') return new Response('', {status: 405});
  const cache = typeof caches !== 'undefined' ? caches.default : null;
  if (cache && !m[2]) {
    const hit = await cache.match(request).catch(() => null);
    if (hit) return hit;
  }
  const s = await env.DB.prepare('SELECT token, user_id, kind, target, label, show_verdict, show_note, show_name FROM share WHERE token=? AND revoked_at IS NULL')
    .bind(m[1]).first();
  if (!s) return notFound();
  const db = env.DB, uid = s.user_id;
  const file = s.kind === 'stage' ? (await db.prepare('SELECT file FROM poster WHERE stage_id=?').bind(s.target).first().catch(() => null))?.file || '' : '';
  if (m[2]) {
    if (!file || !env.POSTERS || !(await r2ReadAllowed(env))) return new Response('', {status: 404});
    const obj = await env.POSTERS.get(file);
    if (!obj) return new Response('', {status: 404});
    return new Response(obj.body, {headers: {'Content-Type': obj.httpMetadata?.contentType || 'image/jpeg', 'Cache-Control': `public, max-age=${PUBLIC_MAX_AGE * 10}`,
      'X-Content-Type-Options': 'nosniff', 'X-Robots-Tag': 'noindex'}});
  }
  const today = localNow().slice(0, 10);
  const name = await whoHtml(db, uid, s);
  let out;
  if (s.kind === 'stage') {
    out = await stageBody(db, uid, s, file);
    if (!out) return notFound();
  } else {
    const ws = s.kind === 'favourites' ? [] : shown(await publicWorks(db, uid), s);
    const label = SHARE_KINDS[s.kind];
    const body = s.kind === 'works' ? await worksBody(ws) : s.kind === 'records' ? await recordsBody(db, uid, ws, today)
      : s.kind === 'favourites' ? await favouritesBody(db, uid) : s.kind === 'chronicle' ? await chronicleBody(db, uid, ws, s) : '';
    const lede = s.kind === 'favourites' ? '' : `<p class="lede">観た公演 ${new Set(ws.map(w => titleKey(w.title))).size} 作品の記録です。</p>`;
    out = {title: `${label} ― たぐり`, card: {title: `観劇の記録（${label}）― たぐり`, description: 'たぐりの利用者が共有した観劇の記録です。'},
      body: `<h1>${E(label)}</h1>${lede}${body}`};
  }
  const res = new Response(page({...out, origin: url.origin, path: url.pathname, name}), {headers: publicHeaders()});
  if (cache) { try { await cache.put(request, res.clone()); } catch { /* 控えられなくても返す */ } }
  return res;
}
