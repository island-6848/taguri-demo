// 興味あり・お気に入り・購入済み公演, and the writes they make (favourite, decline,
// ticket), answered by the Worker from D1 (起案者の指示 2026-10-14「残りの画面も順に移して」).
//
// The lists are app._rebucket for a public user: a stage the user answered goes by the
// newest answer (owned > interest > not interested), a stage matching a registered
// name (recommend2.declared_hits) is a お気に入り; one row per production. Cards are the
// daily batch's (cards.js). Name matching runs in SQL over the normalised texts stored
// with each card (migration 0018), so the Worker never scans every stage itself.
// Left out for now: the name candidates picked from notes (reasons.promotions /
// demotions), the matching of a subject word inside a longer registered subject.
import {stageInfo, fallbackTemplate} from './fallback.js';
import {E, ValueError} from './py.js';
import {compose, cardTemplates, posterHtml, mytixHtml, preNote} from './cards.js';
import {titleKey} from './works.js';
import {indexTabs} from './rate.js';
import {PREFS} from './prefs.js';

export const KINDS = ['団体', '人', '主催', '作品', '原作者', '題材'];
const DECLARED_KEY = 'declared', DECLINED_KEY = 'declined';
const LIST_TOP = 8;
const ROLE_SRC = '公演ページのクレジット';
const ICO = {star: 'M12 3.8l2.5 5.1 5.6.8-4 3.9 1 5.6-5.1-2.7-5.1 2.7 1-5.6-4-3.9 5.6-.8z', flag: 'M5 21V4h13l-2.5 4.5L18 13H5'};
const ico = name => `<svg class="ico " viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${ICO[name]}"/></svg>`;
/** recommend2.nz */
export const nz = s => String(s ?? '').normalize('NFKC').replaceAll(' ', '').replaceAll('　', '').toLowerCase();
const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
const chunks = (xs, n) => Array.from({length: Math.ceil(xs.length / n)}, (_, i) => xs.slice(i * n, i * n + n));
const nowIso = ctx => new Date(ctx.now).toISOString();

async function readJson(ctx, key) {
  const row = await ctx.db.prepare('SELECT value FROM app_setting WHERE user_id=? AND key=?').bind(ctx.uid, key).first();
  try { return JSON.parse(row?.value ?? 'null'); } catch { return null; }
}
async function writeJson(ctx, key, value) {
  await ctx.db.prepare('INSERT INTO app_setting(user_id,key,value,updated_at) VALUES(?,?,?,?) ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at')
    .bind(ctx.uid, key, JSON.stringify(value), nowIso(ctx)).run();
}

/** app.load_declared: kind -> names. The older 「アカウント・記録」 page's favourites count too. */
export async function loadDeclared(ctx) {
  const v = await readJson(ctx, DECLARED_KEY);
  const out = Object.fromEntries(KINDS.map(k => [k, (v && Array.isArray(v[k]) ? v[k] : []).filter(x => typeof x === 'string')]));
  const {results} = await ctx.db.prepare('SELECT name,kind FROM favourites WHERE user_id=? ORDER BY kind,name LIMIT 200').bind(ctx.uid).all();
  for (const f of results) if (out[f.kind] && !out[f.kind].includes(f.name)) out[f.kind].push(f.name);
  return out;
}
/** app.load_declined */
export async function loadDeclined(ctx) {
  const v = await readJson(ctx, DECLINED_KEY);
  return Array.isArray(v) ? v.filter(w => typeof w === 'string' && w.trim()) : [];
}

/** reaction rows merged per stage, newest last (feedback.reactions). */
export async function reactionsOf(ctx) {
  const {results} = await ctx.db.prepare('SELECT stage_id,interest,owned,note,note_no,note_pre FROM reaction WHERE user_id=? ORDER BY updated_at').bind(ctx.uid).all();
  const out = new Map();
  for (const r of results) {
    const d = out.get(r.stage_id) || {};
    if (r.interest !== null) d.interest = Number(r.interest);
    if (r.owned !== null) d.owned = Number(r.owned);
    if (r.note !== null) d.note = r.note;
    if (r.note_no !== null) d.note_no = r.note_no;
    if (r.note_pre !== null && r.note_pre !== undefined) d.note_pre = r.note_pre;
    out.set(r.stage_id, d);
  }
  return out;
}

/** feedback.tickets: stage_id -> tickets, earliest first. */
async function ticketsOf(ctx) {
  const {results} = await ctx.db.prepare('SELECT stage_id,date,time,source,confirmed,uid FROM ticket WHERE user_id=? ORDER BY date,time').bind(ctx.uid).all();
  const out = new Map();
  for (const t of results) {
    if (!out.has(t.stage_id)) out.set(t.stage_id, []);
    out.get(t.stage_id).push({date: t.date, time: t.time || '', source: t.source, confirmed: Number(t.confirmed || 0), uid: t.uid || ''});
  }
  return out;
}

const META = 'stage_id,title,tour,start,end,pref,gnz,blob,ws,synz';
/** recommend2.declared_hits over the stored texts of one card. */
export function declaredLabels(m, declared) {
  const hits = [];
  for (const k of ['団体', '主催']) for (const w of declared[k] || []) if (nz(w) && m.gnz.includes(nz(w))) hits.push(`${k}「${w}」`);
  for (const k of ['人', '作品', '原作者']) for (const w of declared[k] || []) if (nz(w) && m.blob.includes(nz(w))) hits.push(`${k}「${w}」`);
  const ws = m.ws ? m.ws.split('\n') : [];
  const themes = new Set([...(declared['題材'] || []), ...(declared['原作者'] || [])].filter(d => d
    && (ws.some(w => w.includes(nz(d)) || nz(d).includes(w)) || (m.synz && m.synz.includes(nz(d))))));
  for (const w of themes) hits.push(`題材「${w}」`);
  return [...new Set(hits)].sort(cmp);
}
/** recommend2.declined_hit */
export function declinedWord(m, words) {
  const ws = m.ws ? m.ws.split('\n') : [];
  return words.find(w => nz(w) && (m.blob.includes(nz(w)) || ws.some(x => x.includes(nz(w))))) || '';
}

/**
 * Stages (with a card today) whose texts contain any of these normalised needles, read
 * with their columns. One scan of rec_card per chunk; only matching rows come back.
 */
async function cardsMatching(ctx, needles) {
  const out = new Map();
  for (const part of chunks([...new Set(needles.filter(n => n[1]))], 45)) {
    const cond = part.map(([col]) => (col === 'theme' ? '(instr(ws,?)>0 OR instr(synz,?)>0)' : `instr(${col},?)>0`)).join(' OR ');
    const args = part.flatMap(([col, v]) => (col === 'theme' ? [v, v] : [v]));
    const {results} = await ctx.db.prepare(`SELECT ${META} FROM rec_card WHERE ver=(SELECT v FROM rec_meta WHERE k='rec_card') AND (${cond})`).bind(...args).all();
    for (const r of results) out.set(r.stage_id, r);
  }
  return out;
}

/** Card columns of these stages. */
export async function cardMeta(ctx, sids) {
  const out = new Map();
  for (const part of chunks([...new Set(sids)], 90)) {
    const {results} = await ctx.db.prepare(`SELECT ${META} FROM rec_card WHERE ver=(SELECT v FROM rec_meta WHERE k='rec_card') AND stage_id IN (${part.map(() => '?').join(',')})`).bind(...part).all();
    for (const r of results) out.set(r.stage_id, r);
  }
  return out;
}

/** Productions of the stages matching the user's registered names / words not to show. */
export async function nameHits(ctx, declared, words) {
  const needles = [];
  for (const k of ['団体', '主催']) for (const w of declared[k] || []) needles.push(['gnz', nz(w)]);
  for (const k of ['人', '作品', '原作者']) for (const w of declared[k] || []) needles.push(['blob', nz(w)]);
  for (const w of [...(declared['題材'] || []), ...(declared['原作者'] || [])]) needles.push(['theme', nz(w)]);
  const fav = await cardsMatching(ctx, needles);
  const hits = new Map();
  for (const [sid, m] of fav) {
    const a = declaredLabels(m, declared);
    if (a.length) hits.set(sid, {meta: m, a});
  }
  const dec = new Map();
  if (words.length) {
    const rows = await cardsMatching(ctx, words.flatMap(w => [['blob', nz(w)], ['ws', nz(w)]]));
    for (const [sid, m] of rows) {
      const w = declinedWord(m, words);
      const a = hits.get(sid)?.a || [];
      // A registered name wins, except a 主催 alone (a theatre's whole season).
      if (w && !(a.length && !a.every(h => h.startsWith('主催「')))) dec.set(sid, w);
    }
  }
  return {hits, declined: dec};
}

/** app._owned_done_date over the production's stages. */
function doneDate(sids, end, tickets) {
  const confirmed = sids.flatMap(s => (tickets.get(s) || []).filter(t => t.confirmed).map(t => t.date));
  return confirmed.length ? confirmed.sort().at(-1) : (end || '');
}

/**
 * app._promote_owned_tickets: an owned stage whose run (or confirmed ticket) is over
 * becomes a work, so it waits for a rating in 未評価. Never twice, never over a row the
 * user already has for that stage.
 */
export async function promoteOwned(ctx) {
  const react = await reactionsOf(ctx);
  const owned = [...react].filter(([, r]) => r.owned === 1).map(([sid]) => sid);
  if (!owned.length) return;
  const have = new Set((await ctx.db.prepare('SELECT stage_id FROM works WHERE user_id=? AND stage_id IS NOT NULL').bind(ctx.uid).all()).results.map(r => r.stage_id));
  const todo = owned.filter(sid => !have.has(sid));
  if (!todo.length) return;
  const tickets = await ticketsOf(ctx);
  const meta = await cardMeta(ctx, todo);
  const missing = todo.filter(s => !meta.has(s));
  for (const part of chunks(missing, 90)) {
    const qs = part.map(() => '?').join(',');
    const [cur, past] = await Promise.all([
      ctx.db.prepare(`SELECT stage_id,title,end FROM rec_stage WHERE ver=(SELECT v FROM rec_meta WHERE k='current') AND stage_id IN (${qs})`).bind(...part).all(),
      ctx.db.prepare(`SELECT stage_id,title,end FROM past_stage WHERE stage_id IN (${qs})`).bind(...part).all()]);
    for (const r of [...past.results, ...cur.results]) meta.set(r.stage_id, {...r, end: String(r.end || '').replaceAll('/', '-')});
  }
  for (const sid of todo) {
    const m = meta.get(sid);
    const done = doneDate([sid], m?.end || '', tickets);
    if (!m?.title || !done || done > ctx.today) continue;
    const key = `${titleKey(m.title)}#${done}`;
    // The memo written before seeing it (購入済み公演「観る前のメモ」) goes with the work.
    await ctx.db.prepare(`INSERT INTO works(user_id,work_key,title,first_date,last_date,times,verdict,chosen,note_impression,note_motive,stage_id,updated_at)
      VALUES(?,?,?,?,?,1,NULL,NULL,'',?,?,?) ON CONFLICT(user_id,work_key) DO NOTHING`).bind(ctx.uid, key, m.title, done, done, react.get(sid)?.note_pre || '', sid, nowIso(ctx)).run();
  }
}

/** app._rebucket for the three lists: {tracking, favourites, owned, others, declined, react, tickets}. */
export async function buckets(ctx) {
  await promoteOwned(ctx);
  const [react, tickets, declared, words] = await Promise.all([reactionsOf(ctx), ticketsOf(ctx), loadDeclared(ctx), loadDeclined(ctx)]);
  const {hits, declined} = await nameHits(ctx, declared, words);
  const meta = await cardMeta(ctx, [...react.keys()]);
  // Answered stages without a prebuilt card (only in the catalogue, see fallback.js) still count.
  const bare = [...react.keys()].filter(sid => !meta.has(sid));
  if (bare.length) for (const [sid, s] of await stageInfo(ctx.db, bare)) {
    if (s.end && s.end < ctx.today) continue;
    meta.set(sid, {stage_id: sid, title: s.title, tour: '', start: s.start, end: s.end, pref: s.pref, gnz: '', blob: '', ws: '', synz: ''});
  }
  for (const [sid, h] of hits) meta.set(sid, h.meta);
  const tourOf = m => m.tour || 'stage:' + m.stage_id;
  // Every venue of the productions on these lists (an answer is copied to the whole tour).
  const tours = [...new Set([...meta.values()].map(m => m.tour).filter(Boolean))];
  const venues = new Map();
  for (const part of chunks(tours, 90)) {
    const {results} = await ctx.db.prepare(`SELECT ${META} FROM rec_card WHERE ver=(SELECT v FROM rec_meta WHERE k='rec_card') AND tour IN (${part.map(() => '?').join(',')})`).bind(...part).all();
    for (const r of results) { if (!venues.has(r.tour)) venues.set(r.tour, []); venues.get(r.tour).push(r); }
  }
  const out = {tracking: [], favourites: [], owned: [], others: [], react, tickets, declared, words, declined, hits};
  const seen = new Set();
  const order = [...meta.values()].sort((a, b) => cmp(a.start || '9999', b.start || '9999') || cmp(a.stage_id, b.stage_id));
  for (const m of order) {
    const key = tourOf(m);
    if (seen.has(key)) continue;
    const group = m.tour ? (venues.get(m.tour) || [m]) : [m];
    const sids = group.map(v => v.stage_id);
    // The newest answer of any venue of the production decides (owned wins).
    const rs = sids.map(s => react.get(s)).filter(Boolean);
    const r = {owned: rs.some(x => x.owned === 1) ? 1 : undefined,
      interest: rs.find(x => x.interest !== undefined)?.interest};
    const pick = sids.find(s => react.has(s)) || m.stage_id;
    const pre = sids.map(s => react.get(s)?.note_pre).find(Boolean) || '';
    const row = {...(group.find(v => v.stage_id === pick) || m), sids, note: react.get(pick)?.note || '', note_pre: pre};
    if (r.owned === 1) {
      seen.add(key);
      const done = doneDate(sids, row.end, tickets);
      if (done && done <= ctx.today) continue;
      out.owned.push(row);
    } else if (r.interest === 1) { seen.add(key); out.tracking.push(row); }
    else if (r.interest === 0) { seen.add(key); out.others.push(row); }
    else if (hits.has(m.stage_id)) { seen.add(key); out.favourites.push({...row, stage_id: m.stage_id, a: hits.get(m.stage_id).a}); }
  }
  const byStart = (a, b) => cmp(a.start || '9999', b.start || '9999');
  out.tracking.sort(byStart);
  out.favourites.sort(byStart);
  return out;
}

const monthKey = r => (r.start || '').slice(0, 7);
const monthLabel = m => { const [y, mo] = m.split('-'); return mo ? `${y} 年 ${Number(mo)} 月` : '上演日が分からない公演'; };
/** render_recommend.month_pick */
export function monthPick(rows, sel, page, action) {
  const counts = {};
  for (const c of rows) { const k = monthKey(c) || 'none'; counts[k] = (counts[k] || 0) + 1; }
  const months = Object.keys(counts).filter(k => k !== 'none').sort();
  if (counts.none) months.push('none');
  sel = Object.hasOwn(counts, sel) ? sel : '';
  const hit = sel === 'none' ? rows.filter(c => !monthKey(c)) : sel ? rows.filter(c => monthKey(c) === sel) : [...rows];
  const last = Math.max(1, Math.ceil(hit.length / LIST_TOP));
  page = Math.min(Math.max(page, 1), last);
  const show = hit.slice((page - 1) * LIST_TOP, page * LIST_TOP);
  const link = `${action}?t=__TAGURI_TOKEN__`;
  const url = (m, pg) => link + (m ? `&amp;m=${E(m)}` : '') + (pg > 1 ? `&amp;p=${pg}` : '');
  const tabs = indexTabs([['', 'すべて', rows.length], ...months.map(m => [m, monthLabel(m === 'none' ? '' : m), counts[m]])],
    sel, m => url(m, 1), '月で切り替える');
  const where = !sel ? '上演日の近い順' : `<b>${E(monthLabel(sel === 'none' ? '' : sel))}</b>の ${hit.length} 件`;
  const first = (page - 1) * LIST_TOP + 1;
  const now = hit.length <= LIST_TOP ? `${where}で、${hit.length} 件すべてを表示しています。`
    : `${where}の <b>${first}〜${first + show.length - 1} 件目</b>を表示しています（全 ${hit.length} 件）。<b>残りは下の「次の ${LIST_TOP} 件」か、上の見出しのタブから見られます。</b>`;
  const head = `${tabs}<div class="idxsheet loose"><p class="mnow">${now}</p>`;
  if (last <= 1) return [show, head, '</div>'];
  const prev = page > 1 ? `<a class="mpage" href="${url(sel, page - 1)}">← 前の ${LIST_TOP} 件</a>` : '<span class="mpage off">最初のページです</span>';
  const nxt = page < last ? `<a class="mpage" href="${url(sel, page + 1)}">次の ${Math.min(LIST_TOP, hit.length - page * LIST_TOP)} 件 →</a>` : '<span class="mpage off">これで最後です</span>';
  return [show, head, `</div><div class="mfoot">${prev}<span class="mp">${page} / ${last} ページ</span>${nxt}</div>`];
}

/** Filled cards for these rows in one list. */
async function cards(ctx, rows, mode, extra = () => ({})) {
  const {html, posters} = await cardTemplates(ctx.db, rows.map(r => r.stage_id));
  const bare = rows.map(r => r.stage_id).filter(sid => !html.has(sid));
  if (bare.length) for (const [sid, s] of await stageInfo(ctx.db, bare)) html.set(sid, fallbackTemplate(s));
  return rows.filter(r => html.has(r.stage_id)).map(r => {
    const pic = posters.get(r.stage_id) || r.sids?.map(s => posters.get(s)).find(Boolean);
    return compose(html.get(r.stage_id), r.stage_id, mode, {poster: pic ? posterHtml(pic) : '', ...extra(r)});
  });
}
const qInt = (params, k) => Math.max(1, Number.parseInt(params.get(k) || '1', 10) || 1);

export async function interestScreen(params, ctx) {
  const b = await buckets(ctx);
  const rows = b.tracking;
  const [show, mfil, mfoot] = monthPick(rows, params.get('m') || '', qInt(params, 'p'), '/recommend/interest');
  const list = rows.length
    ? '<p class="lead"><b>上演日の近い順</b>に並んでいます。順位は付けていません。</p><div class="tickets">'
      + (await cards(ctx, show, 'interest', r => ({note: r.note}))).join('') + '</div>'
    : '<p class="empty">追いかけている公演はありません。「おすすめ」の画面で「興味あり」を押すと、ここに並びます。</p>';
  const body = `<h1>追いかけている ${rows.length} 件</h1>
<p class="lede">「興味あり」を押した公演を、上演日の近い順に並べています。順位は付けていません。チケットが取れたら「すでに持っている」を押してください。観る予定に移り、上演日を過ぎると評価待ちに並びます。<br>
「なぜ気になったか」に書いた名前は、<a href="/recommend/favourites?t=__TAGURI_TOKEN__">お気に入り</a>に加える候補として並びます。</p>
${mfil}
${list}
${mfoot}`;
  return {title: '興味あり', body_html: body};
}

function declinedBox(words) {
  const tags = words.map(w => `<span class="tag" data-word="${E(w)}">「${E(w)}」<button data-dec="remove">✕</button></span>`).join('');
  return `<details class="pbox" id="declined">
<summary>${ico('flag')}出さない語 <b>${words.length} 語</b></summary>
<p class="lead">ここに入れた語が題名・団体・劇場・出演者・題材のどれかに出てくる公演は、
おすすめに出しません。消してはいないので、語を外せば戻ります。
お気に入りに登録した名前の公演は、この語に当たっても外れません。
<b>ただし「主催」で登録した名前だけで出てきた公演は例外で、この語に当たれば外れます</b>
（劇場が自主で組む公演を丸ごと拾う登録なので、団体・人・作品・原作者のような
狭い登録とは扱いが違います）。</p>
${words.length ? tags : '<p class="empty">まだ 1 つも外していません。</p>'}
<div class="fav-add"><input id="dec-word" type="text"
  placeholder="出さない語（例: バレエ）" size="22">
 <button data-dec="add">出さない</button><span class="said"></span></div>
</details>`;
}

export async function favouritesScreen(params, ctx) {
  const b = await buckets(ctx);
  const favs = b.favourites, dec = b.declared;
  const [show, mfil, mfoot] = monthPick(favs, params.get('m') || '', qInt(params, 'p'), '/recommend/favourites');
  const kinds = KINDS.map(k => `<option value="${E(k)}">${E(k)}</option>`).join('');
  const tags = KINDS.flatMap(k => (dec[k] || []).map(n => `<span class="tag" data-kind="${E(k)}" data-name="${E(n)}">`
    + `<span class="wax" aria-hidden="true">${E(Array.from(n)[0] || '')}</span><span class="tgn">${E(k)}「${E(n)}」</span>`
    + '<button data-fav="remove">✕</button></span>')).join('');
  const keep = !favs.length;
  const n = KINDS.reduce((s, k) => s + (dec[k] || []).length, 0);
  const tools = `<div class="fil2"><details class="pbox" id="names"${keep ? ' open' : ''}>`
    + `<summary>${ico('star')}登録した名前 <b>${n} 件</b> ── 足す・外す</summary>`
    + '<p class="lead">観た記録に無い名前も登録できます。おすすめは ◎ を付けた公演の作り手からしか作れないので、まだ観たことのない劇団や、人から聞いただけの名前は、ここから登録してください。'
    + '<b>表記ゆれ（漢字とカタカナ、送り仮名の違いなど）は自動では気づけません。</b>ありそうなときは、両方の書き方をそれぞれ登録してください。</p>'
    + `<div class="fav-add"><select id="fav-kind">${kinds}</select> <input id="fav-name" type="text" placeholder="団体名・人名・作品名・題材" size="26"> <button data-fav="add">登録する</button>`
    + `<span class="said"></span></div><div class="tags">${tags}</div></details>${declinedBox(b.words)}</div>`;
  const why = r => ({why: r.a.map(w => `<li class="rs a"><span class="net">お気に入り</span>登録した${E(w)}の公演です<span class="src">［出典: ${E(ROLE_SRC)}］</span></li>`).join('')});
  const list = favs.length
    ? '<p class="lead"><b>ここは読むだけです。押すボタンはありません。</b><b>上演日の近い順</b>に並んでいます。順位は付けていません。観ると決めたら、公式サイトから券を求めてください。</p>'
      + `<div class="tickets">${(await cards(ctx, show, 'favourite', why)).join('')}</div>`
    : '<p class="empty">登録した名前に当たる新着はありません。</p>';
  const body = `<h1>お気に入り ── 新着 ${favs.length} 件</h1>
<p class="lede">登録した名前の公演を、件数の制限なしにすべて出します。順位は付けていません。件数が多いので、上演月ごとに分けています。</p>
${tools}
${mfil}
${list}
${mfoot}`;
  return {title: 'お気に入り', body_html: body};
}

export async function ticketsScreen(_params, ctx) {
  const b = await buckets(ctx);
  const rank = r => [PREFS.includes(r.pref) ? PREFS.indexOf(r.pref) : PREFS.length, r.end || '9999-99-99', r.title || ''];
  const owned = [...b.owned].sort((x, y) => { const p = rank(x), q = rank(y); return (p[0] - q[0]) || cmp(p[1], q[1]) || cmp(p[2], q[2]); });
  const mine = r => r.sids.flatMap(s => (b.tickets.get(s) || []).map(t => ({...t, sid: s})))
    .sort((p, q) => cmp(p.date, q.date) || cmp(p.time || '', q.time || ''));
  const html = (await cards(ctx, owned, 'owned', r => ({mytix: mytixHtml(r.stage_id, r.start, r.end, mine(r)) + preNote(r.stage_id, r.note_pre)}))).join('');
  const body = `<h1>購入済み公演 ── ${owned.length} 件</h1>
<p class="lede">「すでに持っている」と答えた公演と、購入確認メールから見つかった公演です。<b>この一覧は、次のおすすめを変えません。</b>上演日を過ぎると一覧から外れ、<a href="/rate?t=__TAGURI_TOKEN__">評価一覧</a>の評価待ちに移ります。行く日は、各公演の「行く日」の欄から入れられます。</p>
${html || '<p class="empty">チケットを持っている公演はまだありません。推薦の画面で「すでに持っている」を押した公演が、ここに並びます。</p>'}
`;
  return {title: '購入済み公演', body_html: body};
}

// ---------------------------------------------------------------- writes
/** serve.on_favourite (public user): add or remove a registered name. */
async function favouriteAction(b, ctx) {
  const action = String(b.action ?? ''), kind = String(b.kind ?? ''), name = String(b.name ?? '').trim().slice(0, 80);
  if (!['add', 'remove'].includes(action) || !KINDS.includes(kind) || !name) throw new ValueError('action（add / remove）・kind・name が要る');
  const v = await readJson(ctx, DECLARED_KEY);
  const d = Object.fromEntries(KINDS.map(k => [k, (v && Array.isArray(v[k]) ? v[k] : []).filter(x => typeof x === 'string')]));
  let cur = d[kind];
  if (action === 'add') { if (!cur.includes(name)) cur.push(name); } else cur = cur.filter(x => x !== name);
  d[kind] = cur;
  // app.save_declared: trimmed, de-duplicated, sorted, at most 100 per kind.
  const out = Object.fromEntries(KINDS.map(k => [k, [...new Set(d[k].map(x => String(x).trim().slice(0, 80)).filter(Boolean))].sort(cmp).slice(0, 100)]));
  await writeJson(ctx, DECLARED_KEY, out);
  if (action === 'remove') await ctx.db.prepare('DELETE FROM favourites WHERE user_id=? AND name=? AND kind=?').bind(ctx.uid, name, kind).run();
  return {body: {ok: true, kind, name, n: cur.length, said: '登録しました。手元にある公演から探して、お気に入りに表示します'}};
}

/** serve.on_decline (public user) */
async function declineAction(b, ctx) {
  const action = String(b.action ?? ''), word = String(b.word ?? '').trim().slice(0, 40);
  if (!['add', 'remove'].includes(action) || !word) throw new ValueError('action（add / remove）と word が要る');
  let cur = await loadDeclined(ctx);
  if (action === 'add') { if (!cur.includes(word)) cur.push(word); } else cur = cur.filter(w => w !== word);
  cur = [...new Set(cur.map(w => w.trim().slice(0, 40)).filter(Boolean))].slice(0, 200);
  await writeJson(ctx, DECLINED_KEY, cur);
  return {body: {ok: true, word, n: cur.length}};
}

/** app.save_ticket: add / confirm / delete one ticket of a stage. */
async function ticketAction(b, ctx) {
  let sid = String(b.stage_id ?? '').trim();
  const date = String(b.date ?? ''), tm = String(b.time ?? '').trim(), action = String(b.action ?? 'add');
  if (!/^\d+$/.test(sid)) throw new ValueError('公演が分かりません');
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) throw new ValueError('日にちは 2026-09-05 の形で入れてください');
  if (tm && !/^\d{2}:\d{2}$/.test(tm)) throw new ValueError('時刻は 14:00 の形で入れてください');
  const db = ctx.db;
  if (action === 'del') {
    await db.prepare('DELETE FROM ticket WHERE user_id=? AND stage_id=? AND date=? AND time=?').bind(ctx.uid, sid, date, tm).run();
  } else if (action === 'confirm') {
    await db.prepare('UPDATE ticket SET confirmed=1, updated_at=? WHERE user_id=? AND stage_id=? AND date=? AND time=?').bind(nowIso(ctx), ctx.uid, sid, date, tm).run();
  } else {
    // app.ticket_target: a date outside this venue's run goes to the production's venue that has it.
    const m = (await cardMeta(ctx, [sid])).get(sid);
    if (m) {
      const inRun = v => (!v.start || v.start <= date) && (!v.end || date <= v.end);
      if (!inRun(m) && m.tour) {
        const {results} = await db.prepare(`SELECT ${META} FROM rec_card WHERE ver=(SELECT v FROM rec_meta WHERE k='rec_card') AND tour=?`).bind(m.tour).all();
        const other = results.find(inRun);
        if (other) sid = other.stage_id;
        else throw new ValueError('上演期間の中の日を入れてください');
      } else if (!inRun(m)) throw new ValueError('上演期間の中の日を入れてください');
    }
    await db.prepare(`INSERT INTO ticket(user_id,stage_id,date,time,source,confirmed,uid,updated_at) VALUES(?,?,?,?,'screen',1,'',?)
      ON CONFLICT(user_id,stage_id,date,time) DO UPDATE SET confirmed=1, updated_at=excluded.updated_at`).bind(ctx.uid, sid, date, tm, nowIso(ctx)).run();
  }
  const {results} = await db.prepare('SELECT date,time,source,confirmed,uid FROM ticket WHERE user_id=? AND stage_id=? ORDER BY date,time').bind(ctx.uid, sid).all();
  return {body: {ok: true, stage_id: sid, tickets: results.map(t => ({date: t.date, time: t.time || '', source: t.source, confirmed: Number(t.confirmed || 0), uid: t.uid || ''}))}};
}

export const listScreens = {
  screens: {interest: interestScreen, favourites: favouritesScreen, tickets: ticketsScreen},
  actions: {favourite: favouriteAction, decline: declineAction, ticket: ticketAction},
};
