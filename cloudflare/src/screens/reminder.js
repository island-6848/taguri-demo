// 開幕リマインド: digest.panel and the parts of render_recommend it uses, ported to the
// Worker (起案者の指示 2026-10-14「残りの画面も順に移して」). reminder.test.js checks the
// panel against digest.panel on the same candidates and answers.
//
// Candidates are the stages of the current index (rec_stage: the pool the batch builds
// from digest.all_candidates). Not ported: the prefecture map (prefmap.panel).
import {E} from './py.js';
import {recordShown} from './evalrec.js';
import {ico, h2} from './icons.js';
import {buttons, changeAnswer, posterHtml, cardTemplates} from './cards.js';
import {stageInfo, detailHtml, detailFromCard} from './fallback.js';
import {indexTabs} from './rate.js';
import {nz, buckets} from './lists.js';
import {prefsFor, prefForm, prefQs, regionCounts, PAGE_PREF_NOTE} from './prefs.js';

export const WINDOW = 7;
export const WEEKS = [['this', '今週'], ['next', '来週']];
const WEEK = '月火水木金土日';
const KIND = {unanswered: ['未回答', 'inbox', 'und'], tracking: ['興味あり', 'flag', 'trk'],
  favourites: ['お気に入り', 'star', 'fav'], declined: ['興味なし', 'tag', 'dec'], cantgo: ['行けない', 'tag', 'dec'], owned: ['購入済', 'ticket', 'own']};
const STATUS_RANK = {unanswered: 0, declined: 1, cantgo: 1, favourites: 2, tracking: 3, owned: 4};
export const REGIONS = [['北海道', ['北海道']], ['東北', ['青森県', '岩手県', '宮城県', '秋田県', '山形県', '福島県']],
  ['関東', ['茨城県', '栃木県', '群馬県', '埼玉県', '千葉県', '東京都', '神奈川県']],
  ['中部', ['新潟県', '富山県', '石川県', '福井県', '山梨県', '長野県', '岐阜県', '静岡県', '愛知県']],
  ['近畿', ['三重県', '滋賀県', '京都府', '大阪府', '兵庫県', '奈良県', '和歌山県']],
  ['中国', ['鳥取県', '島根県', '岡山県', '広島県', '山口県']], ['四国', ['徳島県', '香川県', '愛媛県', '高知県']],
  ['九州・沖縄', ['福岡県', '佐賀県', '長崎県', '熊本県', '大分県', '宮崎県', '鹿児島県', '沖縄県']]];
const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);

// ---------------------------------------------------------------- dates (recommend2 / render_recommend)
const DATE_RE = /(20\d\d)\/(\d{1,2})\/(\d{1,2})/g;
const dates = period => [...String(period || '').matchAll(DATE_RE)].map(m => [Number(m[1]), Number(m[2]), Number(m[3])]);
const iso = ([y, m, d]) => `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
const valid = ([y, m, d]) => { const t = new Date(Date.UTC(y, m - 1, d)); return t.getUTCFullYear() === y && t.getUTCMonth() === m - 1 && t.getUTCDate() === d; };
/** recommend2.period_start / render_recommend._start */
export const periodStart = p => { const ds = dates(p); return ds.length ? iso(ds[0]) : ''; };
/** recommend2.period_end (ISO, '' when unreadable) */
export const periodEnd = p => { const ds = dates(p); return ds.length && valid(ds.at(-1)) ? iso(ds.at(-1)) : ''; };
const addDays = (isoDate, n) => new Date(Date.parse(isoDate + 'T00:00:00Z') + n * 86400000).toISOString().slice(0, 10);
const dayDiff = (a, b) => Math.round((Date.parse(a + 'T00:00:00Z') - Date.parse(b + 'T00:00:00Z')) / 86400000);
const md = isoDate => `${Number(isoDate.slice(5, 7))}/${Number(isoDate.slice(8, 10))}`;

/** render_recommend.run_range */
export function runRange(period, today) {
  const ds = dates(period);
  if (!ds.length || !valid(ds[0]) || !valid(ds.at(-1))) return '';
  let a = ds[0], b = ds.at(-1);
  if (iso(b) < iso(a)) [a, b] = [b, a];
  const year = Number(today.slice(0, 4));
  if (a[0] !== b[0]) return `${a[0]}/${a[1]}/${a[2]}〜${b[0]}/${b[1]}/${b[2]}`;
  const head = a[0] !== year ? `${a[0]}/${a[1]}/${a[2]}` : `${a[1]}/${a[2]}`;
  return iso(a) === iso(b) ? head : `${head}〜${b[1]}/${b[2]}`;
}
const shortPeriod = (period, today) => runRange(period, today) || period;
/** render_recommend.region_label */
export const regionLabel = (pref, fallback = '') => (!pref ? fallback : pref === '北海道' ? pref : '都道府県'.includes(pref.at(-1)) ? pref.slice(0, -1) : pref);

/** render_recommend.venues */
const venue = c => ({stage_id: String(c.stage_id || ''), theater: c.theater || '', pref: c.pref || '', period: c.period || '',
  days: c.days || 0, price: c.price || '', url: c.url || '', onsale: c.onsale || '未確認'});
export const venues = c => [venue(c), ...(c.tours || []).map(venue)];

/** render_recommend.schedule_html */
export function scheduleHtml(c, today, hereLabel = 'このおすすめの日程') {
  let vs = venues(c);
  if (vs.length < 2) return '';
  const here = vs[0].stage_id;
  vs = [...vs].sort((a, b) => cmp(periodStart(a.period) || '9999', periodStart(b.period) || '9999'));
  const rows = vs.map(v => {
    const end = periodEnd(v.period);
    const done = Boolean(end) && end < today;
    const isHere = v.stage_id === here;
    const loc = regionLabel(v.pref, v.theater || '会場未定');
    const theater = v.theater && v.pref ? `<span class="tf-th">／${E(v.theater)}</span>` : '';
    return `<div class="tf-row${done ? ' done' : ''}${isHere ? ' here' : ''}"><span class="tf-loc">${E(loc)}公演${theater}</span>`
      + `<span class="tf-when">${E(shortPeriod(v.period, today))}</span>`
      + (isHere ? `<span class="tf-here">${hereLabel}</span>` : '') + '</div>';
  });
  return `<div class="tourfull">${rows.join('')}</div>`;
}

// ---------------------------------------------------------------- digest
/** recommend2.work_key */
export const workKey = (title, sid = '') => Array.from(nz(title).replace(/[『』「」\s　]/gu, '')).slice(0, 24).join('') || sid;
const regionOf = pref => (REGIONS.find(([, ps]) => ps.includes(pref)) || [pref])[0];
/** digest._loose_title */
export function looseTitle(title) {
  let t = String(title || '').normalize('NFKC').replaceAll(' ', '').replaceAll('　', '').toLowerCase();
  t = t.replace(/[ー－‐−―—–]/gu, '-');
  const m = /^[『「](.+?)[』」](.+)$/su.exec(t);
  if (m && m[2]) t = m[1];
  return t.replace(/[『』「」]/gu, '');
}

/** digest.week_rows over candidates; status: stage_id -> kind key. */
export function weekRows(cands, status, today, offset = 0) {
  const lo = addDays(today, WINDOW * offset), hi = addDays(lo, WINDOW - 1);
  const rows = [];
  for (const c of cands) {
    const s = periodStart(c.period);
    if (!s || !valid(s.split('-').map(Number)) || s < lo || s > hi) continue;
    const sid = String(c.stage_id || '');
    const key = status.get(sid) || 'unanswered';
    // ✕ で候補から消した公演は出さない（起案者の指示 2026-10-18。lists の dismissed）
    if (key === 'dismissed') continue;
    const [kind, icon, cls] = KIND[key];
    rows.push({...c, start: s, stage_id: sid, kind_key: key, kind, icon, cls});
  }
  return rows.sort((a, b) => cmp(a.start, b.start) || cmp(a.title, b.title));
}

// 会場名の表記ゆれ（空白・全角半角）を寄せる
const looseTheater = t => String(t || '').normalize('NFKC').replace(/\s+/gu, '');

// 同じ公演が索引（rec_stage）と一覧（catalogue）に別の番号で載っているときは 1 行にする。会場・初日・題名で見る。
// 終わりの日は鍵に入れない: 一覧の行は終わりの日が無いと初日と同じになり、索引の行と合わなかった
// （起案者の指摘 2026-10-18「開幕リマインドに同じの2個」）
function dedupeCrossSource(rows) {
  const groups = new Map();
  for (const r of rows) {
    const k = JSON.stringify([looseTheater(r.theater), periodStart(r.period), '', looseTitle(r.title)]);
    if (!groups.has(k)) groups.set(k, []);
    groups.get(k).push(r);
  }
  const out = [];
  for (const [k, members] of groups) {
    const [theater, s] = JSON.parse(k);
    if (members.length === 1 || !theater || !s) { out.push(...members); continue; }
    // 残すのは、県と終わりの日が分かる方（索引の行）。暦（cal…）の行は後ろ
    members.sort((a, b) => (String(a.stage_id).startsWith('cal') - String(b.stage_id).startsWith('cal'))
      || (!a.pref - !b.pref) || (periodEnd(b.period) > periodEnd(a.period)) - (periodEnd(a.period) > periodEnd(b.period)));
    out.push(members[0]);
  }
  return out;
}

function mergeSiblings(rows) {
  rows = dedupeCrossSource(rows);
  // 県の分からない行（一覧にだけある行）は、同じ題名の行が 1 つの地方にだけあれば、その地方の束に入れる
  // （県が空だと別の束になり、同じ公演が 2 行になっていた）
  const regionsOf = new Map();
  for (const r of rows) if (r.pref) {
    const w = workKey(r.title, r.stage_id);
    if (!regionsOf.has(w)) regionsOf.set(w, new Set());
    regionsOf.get(w).add(regionOf(r.pref));
  }
  const regionKey = r => {
    if (r.pref) return regionOf(r.pref);
    const rs = regionsOf.get(workKey(r.title, r.stage_id));
    return rs && rs.size === 1 ? [...rs][0] : '';
  };
  const groups = new Map();
  for (const r of rows) {
    const k = workKey(r.title, r.stage_id) + '\u0000' + regionKey(r);
    if (!groups.has(k)) groups.set(k, []);
    groups.get(k).push(r);
  }
  const out = [];
  for (const members of groups.values()) {
    members.sort((a, b) => cmp(a.start, b.start) || cmp(a.stage_id, b.stage_id));
    const head = {...members[0]};
    const seen = new Set([JSON.stringify([head.theater, head.period])]);
    const tail = [];
    for (const m of members.slice(1)) {
      const key = JSON.stringify([m.theater, m.period]);
      if (seen.has(key)) continue;
      seen.add(key);
      tail.push(m);
    }
    if (tail.length) head.tours = tail.map(m => ({stage_id: m.stage_id, theater: m.theater || '', pref: m.pref || '', period: m.period || '',
      days: m.days || 0, price: m.price || '', url: m.url || '', onsale: m.onsale || '未確認'}));
    const best = members.map(m => m.kind_key).reduce((a, b) => (STATUS_RANK[b] > STATUS_RANK[a] ? b : a));
    if (best !== head.kind_key) [head.kind_key, [head.kind, head.icon, head.cls]] = [best, KIND[best]];
    out.push(head);
  }
  // 地方が違って別の行になった同じ公演は、どちらかで答えたら両方の行に同じ答えを出す（起案者の指摘 2026-10-18
  // 「1個だけ興味ありにしたら、もう片方がおすすめに出てきた」）。行を分けるのは 2026-08-26 の指示どおり。
  // 同じ公演とみなすのは、題名が同じで、団体が同じか片方に無いとき（別の団体の同じ題名の上演はまとめない）
  const same = (a, b) => !a.group || !b.group || nz(a.group) === nz(b.group);
  const byTitle = new Map();
  for (const h of out) {
    const w = workKey(h.title, h.stage_id);
    if (!byTitle.has(w)) byTitle.set(w, []);
    byTitle.get(w).push(h);
  }
  for (const heads of byTitle.values()) {
    if (heads.length < 2) continue;
    // 先に全部の行の答えを決めてから入れる（入れながら決めると、団体の無い行を挟んで答えが伝わりすぎる）
    const bests = heads.map(h => heads.filter(o => same(o, h)).map(o => o.kind_key).reduce((a, b) => (STATUS_RANK[b] > STATUS_RANK[a] ? b : a)));
    heads.forEach((h, i) => { if (bests[i] !== h.kind_key) [h.kind_key, [h.kind, h.icon, h.cls]] = [bests[i], KIND[bests[i]]]; });
  }
  return out.sort((a, b) => cmp(a.start, b.start) || cmp(a.title, b.title));
}

/** digest.week_all */
export function weekAll(cands, status, today, prefs = [], offset = 0) {
  const lo = addDays(today, WINDOW * offset), hi = addDays(lo, WINDOW - 1);
  let rows = weekRows(cands, status, today, offset);
  if (prefs.length) rows = rows.filter(r => prefs.includes(r.pref));
  rows = mergeSiblings(rows);
  const days = new Map();
  for (const r of rows) { if (!days.has(r.start)) days.set(r.start, []); days.get(r.start).push(r); }
  return {days: [...days].sort((a, b) => cmp(a[0], b[0])), n: rows.length, lo, hi};
}

const jd = isoDate => `${Number(isoDate.slice(5, 7))}月${Number(isoDate.slice(8, 10))}日（${WEEK[(new Date(isoDate + 'T00:00:00Z').getUTCDay() + 6) % 7]}）`;
// 劇場名は「〇〇劇場（東京都）」の形にそろえる。開幕までの日数（「本日開幕」など）は日付の見出しで分かるので出さない
// （起案者の指示 2026-10-18）。digest._where と同じ
const where = r => (r.venue && r.pref ? `${r.venue}（${r.pref}）` : r.venue || r.pref || '');
// ポスターの無い公演は、灰の地に白い字で「now printing...」（起案者の指示 2026-10-18）
export const NO_POSTER = '<div class="noposter np-print"><span>now printing...</span></div>';
function row(r, today, poster, detail, hereLabel) {
  const answered = ['tracking', 'declined', 'cantgo', 'owned'].includes(r.kind_key);
  const current = {tracking: 'interest', declined: 'nointerest', cantgo: 'cantgo', owned: 'owned'}[r.kind_key] || '';
  const btns = !r.stage_id ? '' : r.kind_key === 'unanswered' ? buttons(r.stage_id) : answered ? changeAnswer(r.stage_id, current) : '';
  const tour = r.tours ? scheduleHtml(r, today, hereLabel) : '';
  const head = `<span class="dgk ${r.cls}">${ico(r.icon, 13)}${E(r.kind)}</span>`
    + `<b class="dgt">${E(r.title)}</b>`
    + `<span class="dgw">${E(where(r))}</span>`;
  const more = detail && r.stage_id ? detail(r.stage_id) : '';
  // Folded by title; opening it shows the run, credits and synopsis like the recommendation cards.
  // ポスターは畳んだ中ではなく、題名の横（開かなくても見える所）に置く（起案者の指示 2026-10-18）
  if (more) return `<li class="dgli dgfold ${r.cls}" data-stage="${E(r.stage_id)}">`
    + `<details class="dgopen"><summary><div class="dghead">${poster(r.stage_id)}<div class="dgbody">${head}</div></div></summary>`
    + `<div class="dgdetail"><div class="dginfo">${more}${tour}</div></div></details>${btns}</li>`;
  return `<li class="dgli ${r.cls}" data-stage="${E(r.stage_id)}">`
    + `${r.stage_id ? poster(r.stage_id) : ''}<div class="dgbody">${head}${tour}</div>${btns}</li>`;
}

/** digest.panel */
// 「直近の観劇予定」の枠は外した（起案者の指示 2026-10-18「下にある『直近の観劇予定』の枠は消す」）。digest.panel と同じ。
// count は週のタブのすぐ下に置く 1 行（画面だけが渡す。digest.panel には無いので、既定は空）
export function panel({cands, status, today, prefs = [], week = 'this', poster = () => '', detail = null, hereLabel = 'このおすすめの日程', pq = '', count = ''}) {
  week = WEEKS.some(([k]) => k === week) ? week : 'this';
  const wks = Object.fromEntries(WEEKS.map(([k], i) => [k, weekAll(cands, status, today, prefs, i)]));
  const wk = wks[week];
  const tabs = indexTabs(WEEKS.map(([k, lab]) => [k, lab, wks[k].n]), week, k => `/recommend/reminder?t=__TAGURI_TOKEN__&w=${k}${pq}`, '週で切り替える');
  const where = prefs.length > 0 && prefs.length <= 3 ? prefs.join('・') : prefs.length ? `${prefs[0]}ほか ${prefs.length - 1} 県` : '';
  const span = `${md(wk.lo)}〜${md(wk.hi)}`;
  let open;
  if (wk.days.length) {
    const days = wk.days.map(([day, rows]) => `<details class="dgday"${dayDiff(day, today) <= 1 ? ' open' : ''}>`
      + `<summary>${jd(day)}　${rows.length} 件</summary>`
      + `<ul class="dglist">${rows.map(r => row(r, today, poster, detail, hereLabel)).join('')}</ul></details>`).join('');
    // 「〇〜〇に開幕する公演 ︰ N 件」の形（起案者の指示 2026-10-18。県で絞ったときも同じ形）
    const lead = prefs.length ? `<b>${E(where)}</b>で ${E(span)} に開幕する公演 ︰ <b>${wk.n} 件</b>`
      : `<b>${E(span)} に開幕する公演 ︰ ${wk.n} 件</b>`;
    open = `<p class="dglead">${lead}</p>${days}`;
  } else if (prefs.length) {
    open = `<p class="dgempty"><b>${E(where)}</b>で ${E(span)} に開幕する公演はありません。</p>`;
  } else {
    open = `<p class="dgempty">${E(span)} に開幕する公演はありません。</p>`;
  }
  const label = Object.fromEntries(WEEKS)[week];
  return `${tabs}${count}
<section class="dgcard dgmain">${h2('inbox', `${label}開幕するすべての公演`)}
${open}</section>`;
}

// ---------------------------------------------------------------- the screen (app._reminder_body)

const chunk90 = xs => Array.from({length: Math.ceil(xs.length / 90)}, (_, i) => xs.slice(i * 90, i * 90 + 90));

/**
 * Stages opening from today to the end of next week, as candidates: the current
 * recommendation index (rec_stage), plus the delivered catalogue for the stages the
 * index does not have. The index is replaced only on days its rows fit the write
 * budget (deliver_catalogue.py skips it otherwise), so on its own it can go stale and
 * leave this screen empty; the catalogue is upserted every day (changed rows only).
 * Catalogue rows carry no prefecture of their own; it comes from venue_pref (by venue name) when known.
 */
export async function openingCandidates(ctx) {
  const hi = addDays(ctx.today, WINDOW * WEEKS.length - 1);
  const {results} = await ctx.db.prepare("SELECT stage_id,title,entry FROM rec_stage WHERE ver=(SELECT v FROM rec_meta WHERE k='current') AND start>=? AND start<=? ORDER BY stage_id")
    .bind(ctx.today, hi).all();
  const out = results.map(r => ({...JSON.parse(r.entry || '{}'), title: r.title, stage_id: r.stage_id}));
  const have = new Set(out.map(c => String(c.stage_id)));
  // The catalogue has no prefecture; venue_pref (migration 0024) gives it by venue name.
  const cat = await ctx.db.prepare('SELECT c.id,c.title,c.date,c.venue,c.url,c.metadata,vp.pref AS vpref FROM catalogue c LEFT JOIN venue_pref vp ON vp.venue=c.venue WHERE c.date>=? AND c.date<=? ORDER BY c.id').bind(ctx.today, hi).all();
  const slash = d => d.replaceAll('-', '/');
  for (const r of cat.results) {
    if (have.has(String(r.id))) continue;
    let m = {};
    try { m = JSON.parse(r.metadata || '{}') || {}; } catch { /* no metadata */ }
    const end = /^\d{4}-\d{2}-\d{2}$/.test(m.end_date || '') ? m.end_date : r.date;
    out.push({stage_id: String(r.id), title: r.title, period: `${slash(r.date)} ～ ${slash(end)}`, theater: r.venue || '', venue: r.venue || '', pref: r.vpref || '',
      group: m.group || '', ...(m.fields ? {fields: m.fields} : {}), ...(r.url ? {url: r.url} : {})});
  }
  return out;
}

/** stage_id -> kind key for every venue of the user's answered / registered productions. */
export function statusOf(b) {
  const out = new Map();
  for (const [key, kind] of [['others', 'declined'], ['favourites', 'favourites'], ['tracking', 'tracking'], ['owned', 'owned']])
    for (const r of b[key]) for (const sid of r.sids || [r.stage_id]) out.set(sid, r.dismissed ? 'dismissed' : r.cantgo ? 'cantgo' : kind);
  return out;
}

async function postersOf(ctx, sids) {
  const out = new Map();
  for (const part of chunk90([...new Set(sids)])) {
    const {results} = await ctx.db.prepare(`SELECT stage_id,file FROM poster WHERE stage_id IN (${part.map(() => '?').join(',')})`).bind(...part).all();
    for (const r of results) out.set(r.stage_id, r.file);
  }
  return out;
}

// The folded rows' few rules come with the screen (public/style.css is the demo's copy).
const FOLD_STYLE = `<style>
.dgli.dgfold{display:block}
.dgfold details.dgopen>summary{cursor:pointer}
.dgdetail{display:flex;gap:12px;align-items:flex-start;margin:10px 0 4px}
.dgdetail .dginfo{flex:1 1 auto;min-width:0;display:grid;gap:8px;font-size:13.5px}
.dgdetail .syn .txt{margin:0}
.dgfold .btns{margin-top:8px}
</style>`;

export async function reminderScreen(params, ctx) {
  const prefs = await prefsFor(params, ctx);
  const w = params.get('w') || 'this';
  const week = WEEKS.some(([k]) => k === w) ? w : 'this';
  const offset = WEEKS.findIndex(([k]) => k === week);
  const [cands, b] = await Promise.all([openingCandidates(ctx), buckets(ctx)]);
  const status = statusOf(b);
  const wr = weekRows(cands, status, ctx.today, offset);
  const counts = {};
  for (const r of wr) if (r.pref) counts[r.pref] = (counts[r.pref] || 0) + 1;
  const label = Object.fromEntries(WEEKS)[week];
  // 場所の説明はどのページでも同じ（起案者の指示 2026-10-18）。以前の「今週のおすすめと同じ絞り込み」は 2026-10-17 から違う（絞り込みはページの中だけ）
  const note = PAGE_PREF_NOTE;
  const pics = await postersOf(ctx, cands.map(c => c.stage_id));
  // What each row of this week shows when opened: the prebuilt card's parts, or (a stage
  // only in the catalogue) its credits and synopsis from there (fallback.js).
  // 都道府県が分からない公演（一覧 catalogue にだけあり、索引に無い公演）は、場所で絞ると落ちる。開幕リマインドは
  // 見逃しを防ぐ画面なので隠さず、絞った一覧の下に別にまとめて出す（起案者の指摘 2026-10-15「場所絞ったら開幕リマインド0件になる」）
  const main = weekAll(cands, status, ctx.today, prefs, offset).days.flatMap(([, rows]) => rows);
  // 絞った一覧に同じ題名で出ている公演は、県の分からない箱には重ねて出さない
  const mainKeys = new Set(main.map(r => workKey(r.title, r.stage_id)));
  const unknown = prefs.length ? weekAll(cands, status, ctx.today, [], offset).days.flatMap(([, rows]) => rows)
    .filter(r => !r.pref && !mainKeys.has(workKey(r.title, r.stage_id))) : [];
  const shown = [...main.map(r => r.stage_id), ...unknown.map(r => r.stage_id)].filter(Boolean);
  // その日に出した公演（測るための記録 rec_shown。点と関係なく出す画面なので、偏りの少ない分母になる）
  await recordShown(ctx, 'reminder', shown);
  const {html: cardHtml} = await cardTemplates(ctx.db, shown);
  const details = new Map([...cardHtml].map(([sid, h]) => [sid, detailFromCard(h)]));
  const bare = shown.filter(sid => !details.has(sid));
  if (bare.length) for (const [sid, s] of await stageInfo(ctx.db, bare)) details.set(sid, detailHtml(s));
  const poster = sid => (pics.has(sid) ? posterHtml(pics.get(sid)) : NO_POSTER), detail = sid => details.get(sid) || '';
  // 件数の 1 行は、今週・来週を選ぶタブの下に置く（起案者の指示 2026-10-18）
  const count = `\n<p class="rcount"><b>${prefs.length ? E(prefs.length <= 3 ? prefs.join('・') : `${prefs[0]}ほか ${prefs.length - 1} 県`) : '全国'}</b>／${E(label)}開幕する公演 ${main.length} 件を表示中</p>`;
  const html = panel({cands, status, today: ctx.today, prefs, week, poster, detail, hereLabel: 'この行の会場', pq: prefQs(params), count});
  const unknownHtml = !unknown.length ? '' : `<details class="dgday" open><summary>都道府県が分からない公演　${unknown.length} 件</summary>`
    + '<p class="dglead">会場の都道府県がまだ分からないため、場所の絞り込みに入れられない公演です。見逃さないように、ここに分けて出しています。</p>'
    + `<ul class="dglist">${unknown.map(r => row(r, ctx.today, poster, detail, 'この行の会場')).join('')}</ul></details>`;
  // 見出しと前置きの 1 文は起案者の指示 2026-10-18 の文面。見出しの下に見えるように置くので、ⓘ に移る p.lede ではなく p.hsub
  const body = `<h1>開幕リマインド</h1>
<p class="hsub">開幕リマインドでは、おすすめやお気に入りにかかわらず、今週・来週開幕予定の公演を全件掲載しています。</p>
<p class="fgh">${ico('search', 15)}<b>表示の絞り込み</b><span>初日が近い公演の中から、表示する項目を設定できます。</span></p>
<div class="fil2 narrow">${prefForm(counts, prefs, '/recommend/reminder', note, {w: week}, regionCounts(wr.map(r => ({key: r.stage_id || r.title, prefs: [r.pref]}))))}</div>
${FOLD_STYLE}
${unknownHtml && html.endsWith('</section>') ? html.slice(0, -'</section>'.length) + unknownHtml + '</section>' : html}`;
  return {title: '開幕リマインド', body_html: body};
}

export const reminderScreens = {screens: {reminder: reminderScreen}, actions: {}};
