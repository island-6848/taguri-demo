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
import {shareStageButton, sharePageButton, withShareButton} from '../share.js';
import {stageInfo, fallbackTemplate} from './fallback.js';
import {parseCredits} from './credits.js';
import {loadWorks} from './works.js';
import {peopleByKey} from './diary.js';
import {gradeText} from './grade.js';
import {r2ReadAllowed} from '../free-tier.js';
import {E, ValueError} from './py.js';
import {compose, cardTemplates, posterHtml, mytixHtml, preNote} from './cards.js';
import {titleKey} from './works.js';
import {indexTabs} from './rate.js';
import {themeExpansion} from '../vocab.js';
import {PREFS, prefsFor, prefForm, prefQs, prefHidden, regionCounts, PAGE_PREF_NOTE} from './prefs.js';
import {CONTENT_AXES} from '../recommend.js';
import {rankedGroups, reasonRows, withTour} from './recommend.js';
import {tourBlock} from './schedule.js';
import {emptyGuide} from './guide.js';

export const KINDS = ['団体', '人', '主催', '作品', '原作者', '題材'];
const DECLARED_KEY = 'declared', DECLINED_KEY = 'declined', DECLARED_AT_KEY = 'declared_at';
// 「この理由を使わない」にした種類（起案者の指示 2026-10-16「自分に合わないなと思うおすすめ理由を消すことはできる？」、
// q-kind-reason-off）。'#原作\tオリジナル' の形で控え、点数にも理由にも使わない。公演そのものは消さない
export const KIND_OFF_KEY = 'kind_off', KIND_OFF_MAX = 100;
const LIST_TOP = 8;
const ICO = {search: 'M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM16.2 16.2 21 21', star: 'M12 3.8l2.5 5.1 5.6.8-4 3.9 1 5.6-5.1-2.7-5.1 2.7 1-5.6-4-3.9 5.6-.8z', flag: 'M5 21V4h13l-2.5 4.5L18 13H5'};
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
// 人で登録した名前を役職で絞る（起案者の指示 2026-10-18「お気に入りの加藤拓也、同姓同名が2人いるみたいでどっちも拾っちゃう」
// への答え「Aで。ただし人って選んだあとに、細く指定したい場合のみ任意で選べるように。複数役職やる人もいるので」、q-favourite-homonym）。
// 控えは app_setting の 'declared_roles'（{名前: [選んだ役職の札]}）。札が無い名前は、これまでどおりどの役職でも当てる
const ROLES_KEY = 'declared_roles';
// 札 -> 出演・スタッフ欄の役職（credits.canonRole の後）。「作・演出」のような並びは、・／ で切った 1 つずつでも当てる
export const FAV_ROLES = [['出演', ['出演']], ['脚本', ['脚本', '作', '潤色', '構成', '脚色']], ['演出', ['演出', '演出・振付']],
  ['作曲・音楽', ['作曲', '音楽', '音楽監督', '編曲', '作詞']], ['振付', ['振付', '演出・振付']], ['翻訳', ['翻訳', '訳']], ['原作', ['原作']]];
const FAV_ROLE_OF = new Map(FAV_ROLES);
/** {名前: [札]} of the 人 names narrowed by role. */
export async function loadRoles(ctx) {
  const v = await readJson(ctx, ROLES_KEY);
  const out = {};
  if (v && typeof v === 'object') for (const [n, rs] of Object.entries(v)) {
    const ok = Array.isArray(rs) ? rs.filter(r => FAV_ROLE_OF.has(r)) : [];
    if (ok.length) out[n] = ok;
  }
  return out;
}
/** The credit roles one name's labels allow, or null (any role). */
export function rolesAllowed(labels) {
  if (!labels || !labels.length) return null;
  return new Set(labels.flatMap(l => FAV_ROLE_OF.get(l) || []));
}
/** Does a credit role (「作・演出」 too) fall in the allowed set? */
export function roleFits(role, allowed) {
  if (!allowed) return true;
  const r = String(role || '');
  return allowed.has(r) || r.split(/[・／/]/u).some(x => allowed.has(x.trim()));
}
/** The optional role boxes under the favourite form (shown only for 人, theme.css「お気に入りの役職」). */
export function favRoleBox() {
  return '<fieldset class="fav-roles"><legend>役職で絞る<small class="opt">任意</small></legend>'
    + FAV_ROLES.map(([l]) => `<label><input type="checkbox" value="${E(l)}"> ${E(l)}</label>`).join('')
    + '<span class="fr-note">同姓同名の人がいるときなどに。選ばなければ、どの役職でも当てます。複数選べます。</span></fieldset>';
}

// 出さない語の対象（起案者の指示 2026-10-18「出さない語も、お気に入りと同様どれを対象に（ジャンルや人、団体など）を
// 選んでから語を指定できるように」）。控えは '対象\t語'。対象の無い語（これまでに入れた語・理由の ✕ で足した語）は「すべて」
export const DEC_KINDS = [['', 'すべて'], ['題名', '題名'], ['団体', '団体'], ['人', '人'], ['劇場', '劇場'], ['題材', '題材'], ['種類', 'ジャンル・形式']];
const DEC_KIND_SET = new Set(DEC_KINDS.map(([k]) => k));
/** '対象\t語' or '語' -> {kind, word} */
export function decEntry(e) {
  const i = String(e).indexOf('\t');
  return i > 0 && DEC_KIND_SET.has(String(e).slice(0, i)) ? {kind: String(e).slice(0, i), word: String(e).slice(i + 1)} : {kind: '', word: String(e)};
}
/** app.load_declined */
export async function loadDeclined(ctx) {
  const v = await readJson(ctx, DECLINED_KEY);
  return Array.isArray(v) ? v.filter(w => typeof w === 'string' && w.trim()) : [];
}

/** Kind reasons the user turned off, as '#axis\ttag' keys (kindOffAction). */
export async function loadKindOff(ctx) {
  const v = await readJson(ctx, KIND_OFF_KEY);
  return Array.isArray(v) ? v.filter(k => typeof k === 'string' && /^#[^\t]+\t[^\t]+$/.test(k)) : [];
}

/** reaction rows merged per stage, newest last (feedback.reactions). */
export async function reactionsOf(ctx) {
  const {results} = await ctx.db.prepare('SELECT stage_id,interest,owned,note,note_no,note_pre,why,source,updated_at FROM reaction WHERE user_id=? ORDER BY updated_at').bind(ctx.uid).all();
  const out = new Map();
  for (const r of results) {
    const d = out.get(r.stage_id) || {};
    // src: the screen the newest 興味あり／なし was pressed on ('reminder', 'search', 'screen' …)
    if (r.interest !== null) { d.interest = Number(r.interest); d.src = String(r.source || '').replace(/_tour$/, ''); }
    if (r.owned !== null) d.owned = Number(r.owned);
    // at: when the newest 興味あり／持っている was pressed (the list's 「追加した新しい順」)
    if (r.interest !== null || r.owned !== null) d.at = String(r.updated_at || '');
    if (r.note !== null) d.note = r.note;
    if (r.note_no !== null) d.note_no = r.note_no;
    if (r.note_pre !== null && r.note_pre !== undefined) d.note_pre = r.note_pre;
    // why: the reasons shown on おすすめ when 興味あり was pressed there (migrations/0026.sql)
    if (r.why) { try { d.why = JSON.parse(r.why); } catch { /* a broken row shows no reasons */ } }
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
/** 登録した題材を語彙表で下位に広げた言葉（正規化済み）。SQL で絞る入れ口に足す。決めるのは declaredLabels。 */
const expandedThemes = declared => [...new Set((declared['題材'] || []).flatMap(d => [...themeExpansion(d).narrow]))].sort(cmp);

/** recommend2.declared_hits over the stored texts of one card. */
export function declaredLabels(m, declared) {
  const hits = [];
  for (const k of ['団体', '主催']) for (const w of declared[k] || []) if (nz(w) && m.gnz.includes(nz(w))) hits.push(`${k}「${w}」`);
  for (const k of ['人', '作品', '原作者']) for (const w of declared[k] || []) if (nz(w) && m.blob.includes(nz(w))) hits.push(`${k}「${w}」`);
  const ws = m.ws ? m.ws.split('\n') : [];
  const themes = new Set([...(declared['題材'] || []), ...(declared['原作者'] || [])].filter(d => d
    && (ws.some(w => w.includes(nz(d)) || nz(d).includes(w)) || (m.synz && m.synz.includes(nz(d))))));
  // 語彙表で下位に広げた言葉（「科学」→ SF・宇宙…）は、#題材 の言葉と丸ごと一致したときだけ（src/vocab.js）
  for (const d of declared['題材'] || []) if (!themes.has(d) && ws.some(w => themeExpansion(d).narrow.has(w))) themes.add(d);
  for (const w of themes) hits.push(`題材「${w}」`);
  return [...new Set(hits)].sort(cmp);
}
/** recommend2.declined_hit */
export function declinedWord(m, words) {
  const ws = m.ws ? m.ws.split('\n') : [];
  for (const e of words) {
    const {kind, word} = decEntry(e), w = nz(word);
    if (!w) continue;
    const hit = kind === '' ? (m.blob.includes(w) || ws.some(x => x.includes(w)))
      : kind === '題名' ? nz(m.title || '').includes(w)
        : kind === '団体' ? (m.gnz || '').includes(w)
          : kind === '人' || kind === '劇場' ? m.blob.includes(w)
            : kind === '題材' ? ws.some(x => x.includes(w)) : false;   // 種類は kindTagged が当てる
    if (hit) return word;
  }
  return '';
}

/**
 * Stages (with a card today) whose texts contain any of these normalised needles, read
 * with their columns. One scan of rec_card per chunk; only matching rows come back.
 */
async function cardsMatching(ctx, needles) {
  const out = new Map();
  // 1 回の問い合わせは rec_card を端から読むので、束はバインドの数（D1 は 100 まで）で詰める。
  // 'theme' は 2 つ、ほかは 1 つ（語彙表で広げた言葉は 'ws' で来る）
  const parts = [];
  let part = [], binds = 0;
  for (const n of new Map(needles.filter(n => n[1]).map(n => [n.join('\u0000'), n])).values()) {
    const b = n[0] === 'theme' ? 2 : 1;
    if (binds + b > 98) { parts.push(part); part = []; binds = 0; }
    part.push(n); binds += b;
  }
  if (part.length) parts.push(part);
  for (const part of parts) {
    const cond = part.map(([col]) => (col === 'theme' ? '(instr(ws,?)>0 OR instr(synz,?)>0)' : `instr(${col},?)>0`)).join(' OR ');
    const args = part.flatMap(([col, v]) => (col === 'theme' ? [v, v] : [v]));
    const {results} = await ctx.db.prepare(`SELECT ${META} FROM rec_card WHERE ver=(SELECT v FROM rec_meta WHERE k='rec_card') AND (${cond})`).bind(...args).all();
    for (const r of results) out.set(r.stage_id, r);
  }
  return out;
}

/**
 * Stages only in the delivered catalogue (no prebuilt card: the cards and the index are
 * replaced only on days they fit the write budget) whose texts contain one of the
 * registered names, as card columns. 起案者の指示（2026-10-14）「たぐりが集めている公演から
 * 出してよ勿論」: a name added to お気に入り is looked up in everything collected, at once.
 * The SQL only narrows; declaredLabels decides on the normalised texts.
 */
async function catalogueMatching(ctx, declared, skip) {
  // Narrowed by the name's first two characters: the catalogue may write 「山田 花子」 for
  // 「山田花子」, and the range of dates is read in full anyway (declaredLabels decides).
  const names = [...new Set([...KINDS.flatMap(k => declared[k] || []), ...expandedThemes(declared)].map(w => Array.from(nz(w)).slice(0, 2).join('')).filter(w => Array.from(w).length >= 2))];
  const out = new Map();
  if (!names.length) return out;
  const since = new Date(Date.parse(ctx.today + 'T00:00:00Z') - 120 * 86400000).toISOString().slice(0, 10);
  for (const part of chunks(names, 45)) {
    let results;
    try {
      ({results} = await ctx.db.prepare(`SELECT id,title,date,venue,metadata FROM catalogue WHERE date>=? AND (${part.map(() => '(instr(lower(title),?)>0 OR instr(lower(metadata),?)>0)').join(' OR ')})`)
        .bind(since, ...part.flatMap(w => [w, w])).all());
    } catch { return out; }
    for (const r of results) {
      const sid = String(r.id);
      if (skip.has(sid) || out.has(sid)) continue;
      let m = {};
      try { m = JSON.parse(r.metadata || '{}') || {}; } catch { /* no metadata */ }
      const end = /^\d{4}-\d{2}-\d{2}$/.test(m.end_date || '') ? m.end_date : r.date;
      if (end < ctx.today) continue;
      const fields = m.fields && typeof m.fields === 'object' ? m.fields : {};
      const words = Array.isArray(m.words) ? m.words.map(String) : [];
      out.set(sid, {stage_id: sid, title: r.title, tour: '', start: r.date, end, pref: '', gnz: nz(m.group || ''),
        blob: nz([r.title, m.group || '', r.venue || '', ...Object.values(fields).map(String)].join('\n')),
        ws: words.map(nz).join('\n'), synz: nz(m.synopsis || '')});
    }
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

/**
 * 人で登録した名前は、名前の一部ではなく名前全体で当てる（起案者の指摘 2026-10-15「お気に入りで「上村聡」を
 * 登録したら、「上村聡史」まで拾っちゃってる」）。本文の文字列（blob）は空白を詰めてあるので、文字列の中で
 * 名前の切れ目は分からない。そこで、当たった公演の出演・スタッフ欄を名前ごとに切り分け（credits.parseCredits）、
 * 登録した名前と同じ名前があるときだけ残す。欄を読めない公演（出演欄が無い等）は、これまでどおり文字列で当てる。
 */
async function wholePersonNames(ctx, hits, declared) {
  const persons = declared['人'] || [];
  if (!persons.length) return;
  const sids = [...hits].filter(([, h]) => h.a.some(x => x.startsWith('人「'))).map(([sid]) => sid);
  if (!sids.length) return;
  // 役職で絞った名前（loadRoles）は、その役職で欄に書かれているときだけ当てる。欄を読めない公演では役職を確かめられないので外す
  const roles = await loadRoles(ctx);
  const allowedOf = new Map(Object.entries(roles).map(([n, ls]) => [nz(n), rolesAllowed(ls)]));
  const info = await stageInfo(ctx.db, sids);
  for (const sid of sids) {
    const people = parseCredits(info.get(sid)?.fields || {});
    const h = hits.get(sid);
    if (!people.length) {
      if (allowedOf.size) h.a = h.a.filter(x => !x.startsWith('人「') || !allowedOf.has(nz(x.slice(2, -1))));
    } else {
      const names = new Set(people.map(([, n]) => nz(n)));
      h.a = h.a.filter(x => {
        if (!x.startsWith('人「')) return true;
        const n = nz(x.slice(2, -1)), allowed = allowedOf.get(n);
        return allowed ? people.some(([r, p]) => nz(p) === n && roleFits(r, allowed)) : names.has(n);
      });
    }
    if (!h.a.length) hits.delete(sid);
  }
}

/** Productions of the stages matching the user's registered names / words not to show. */
export async function nameHits(ctx, declared, words, {catalogue = false} = {}) {
  const needles = [];
  for (const k of ['団体', '主催']) for (const w of declared[k] || []) needles.push(['gnz', nz(w)]);
  for (const k of ['人', '作品', '原作者']) for (const w of declared[k] || []) needles.push(['blob', nz(w)]);
  for (const w of [...(declared['題材'] || []), ...(declared['原作者'] || [])]) needles.push(['theme', nz(w)]);
  for (const w of expandedThemes(declared)) needles.push(['ws', w]);
  const fav = await cardsMatching(ctx, needles);
  // The catalogue scan reads every coming stage, so only お気に入り itself asks for it.
  if (catalogue) for (const [sid, m] of await catalogueMatching(ctx, declared, new Set(fav.keys()))) fav.set(sid, m);
  const hits = new Map();
  for (const [sid, m] of fav) {
    const a = declaredLabels(m, declared);
    if (a.length) hits.set(sid, {meta: m, a});
  }
  await wholePersonNames(ctx, hits, declared);
  const dec = new Map();
  if (words.length) {
    const rows = await cardsMatching(ctx, words.flatMap(e => {
      const {kind, word} = decEntry(e), w = nz(word);
      return kind === '' ? [['blob', w], ['ws', w]] : kind === '団体' ? [['gnz', w]] : kind === '題材' ? [['ws', w]]
        : kind === '種類' ? [] : [['blob', w]];
    }));
    for (const [sid, m] of rows) {
      const w = declinedWord(m, words);
      const a = hits.get(sid)?.a || [];
      // A registered name wins, except a 主催 alone (a theatre's whole season).
      if (w && !(a.length && !a.every(h => h.startsWith('主催「')))) dec.set(sid, w);
    }
  }
  // おすすめ理由の種類（#形式 ミュージカル、#原作の国 韓国、#ジャンル 2.5次元 …）にだけ出てくる語も当てる
  // （起案者の指摘 2026-10-16「出さない語が反映されてない」）。種類の印は本文（blob）に無いことがあるので、
  // 索引の (種類, 語) を主キーで引く
  for (const [sid, w] of await kindTagged(ctx, words)) {
    const a = hits.get(sid)?.a || [];
    if (!dec.has(sid) && !(a.length && !a.every(h => h.startsWith('主催「')))) dec.set(sid, w);
  }
  return {hits, declined: dec};
}

/** stage_id -> the word, for the stages whose kind tags (CONTENT_AXES) are one of these words. */
async function kindTagged(ctx, words) {
  const out = new Map();
  // 対象が「すべて」か「ジャンル・形式」の語だけ
  const ws = [...new Set(words.map(decEntry).filter(d => d.kind === '' || d.kind === '種類').map(d => d.word.trim()).filter(Boolean))];
  if (!ws.length) return out;
  const keys = ws.flatMap(w => CONTENT_AXES.map(axis => [axis, w]));
  for (const part of chunks(keys, 45)) {
    const {results} = await ctx.db.prepare(`SELECT person, stage_id FROM rec_credit WHERE ver=(SELECT v FROM rec_meta WHERE k='current') AND (role,person) IN (VALUES ${part.map(() => '(?,?)').join(',')})`)
      .bind(...part.flat()).all();
    for (const r of results) if (!out.has(r.stage_id)) out.set(r.stage_id, r.person);
  }
  return out;
}

/** app._owned_done_date over the production's stages: the last confirmed ticket ({date, time}) or the run's end ({date}). */
function doneDate(sids, end, tickets) {
  const confirmed = sids.flatMap(s => (tickets.get(s) || []).filter(t => t.confirmed)).sort((a, b) => cmp(a.date + (a.time || ''), b.date + (b.time || '')));
  return confirmed.length ? {date: confirmed.at(-1).date, time: confirmed.at(-1).time || ''} : {date: end || '', time: ''};
}
/**
 * 観に行く回の開演を過ぎたか（日本時間）。起案者の指示 2026-10-18「購入済み公演は、観に行く日の公演開始時間過ぎてから未評価に移して」。
 * 前は行く日（または千穐楽）の 0 時に購入済の公演から消え、未評価には開演を過ぎてから入るので、その日の開演まではどちらにも出なかった。
 * 開演の時刻が分からない回は、その日のうちは購入済に残し、次の日に移す
 */
export function startPassed(date, time, ctx) {
  if (!date) return false;
  if (date < ctx.today) return true;
  if (date > ctx.today || !time) return false;
  return time <= new Date((ctx.now ?? Date.now()) + 9 * 3600e3).toISOString().slice(11, 16);
}

/**
 * app._promote_owned_tickets: an owned stage whose run (or confirmed ticket) is over
 * becomes a work, so it waits for a rating in 未評価. Never twice, never over a row the
 * user already has for that stage.
 */
export async function promoteOwned(ctx) {
  const react = await reactionsOf(ctx);
  await promoteTickets(ctx, react);
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
    const {date: done, time} = doneDate([sid], m?.end || '', tickets);
    if (!m?.title || !startPassed(done, time, ctx)) continue;
    const key = `${titleKey(m.title)}#${done}`;
    // The memo written before seeing it (購入済み公演「観る前のメモ」) goes with the work.
    await ctx.db.prepare(`INSERT INTO works(user_id,work_key,title,first_date,last_date,times,verdict,chosen,note_impression,note_motive,stage_id,updated_at)
      VALUES(?,?,?,?,?,1,NULL,NULL,'',?,?,?) ON CONFLICT(user_id,work_key) DO NOTHING`).bind(ctx.uid, key, m.title, done, done, react.get(sid)?.note_pre || '', sid, nowIso(ctx)).run();
  }
}

/** 公演の題名と会期（カード → 索引 → 過去の公演の順に引く）。 */
async function titlesOf(ctx, sids) {
  const meta = await cardMeta(ctx, sids);
  const missing = sids.filter(s => !meta.has(s));
  for (const part of chunks(missing, 90)) {
    const qs = part.map(() => '?').join(',');
    const [cur, past] = await Promise.all([
      ctx.db.prepare(`SELECT stage_id,title,end FROM rec_stage WHERE ver=(SELECT v FROM rec_meta WHERE k='current') AND stage_id IN (${qs})`).bind(...part).all(),
      ctx.db.prepare(`SELECT stage_id,title,end FROM past_stage WHERE stage_id IN (${qs})`).bind(...part).all()]);
    for (const r of [...past.results, ...cur.results]) meta.set(r.stage_id, {...r, end: String(r.end || '').replaceAll('/', '-')});
  }
  return meta;
}

/**
 * 行く日が過ぎた券は、その回の記録（未評価）にする（起案者の指示 2026-10-18「購入済みの公演で、行く日に過去の日を入れても
 * 『評価する記録』にするために、行く日が過ぎたら自動で未評価に入れるようにして」）。前は購入済みの公演が千穐楽を過ぎるまで
 * 何も起きず、会期の途中の回は手で足し直すしかなかった。
 * - 過ぎた: 行く日が今日より前、または今日で開演の時刻を過ぎた（日本時間）
 * - 同じ公演・同じ日の記録がもうあれば作らない（開演の時刻がどちらかに無いか、同じとき）。同じ日の別の回は時刻で分ける
 * - 本人が記録を消すと、その回の券も消える（works.deleteWork）ので、作り直さない
 * 開く画面（未評価・評価一覧・お気に入り・開幕リマインド）ごとに、この人の券と記録を数行読むだけ。書くのは新しい回の分だけ
 */
async function promoteTickets(ctx, react) {
  const tickets = await ticketsOf(ctx);
  const due = [];
  for (const [sid, ts] of tickets) for (const t of ts) if (startPassed(t.date, t.time, ctx)) due.push({sid, ...t});
  if (!due.length) return;
  const {results} = await ctx.db.prepare('SELECT work_key,stage_id,first_date,time FROM works WHERE user_id=? AND stage_id IS NOT NULL').bind(ctx.uid).all();
  const keys = new Set(results.map(r => r.work_key));
  const same = t => results.some(r => String(r.stage_id) === String(t.sid) && r.first_date === t.date && (!r.time || !t.time || r.time === t.time));
  const todo = due.filter(t => !same(t));
  if (!todo.length) return;
  const meta = await titlesOf(ctx, [...new Set(todo.map(t => t.sid))]);
  for (const t of todo) {
    const m = meta.get(t.sid);
    if (!m?.title) continue;
    let key = `${titleKey(m.title)}#${t.date}`;
    if (keys.has(key)) { if (!t.time) continue; key = `${key}#${t.time}`; }
    if (keys.has(key)) continue;
    keys.add(key);
    // 観る前のメモ（購入済みの公演の「観る前のメモ」）は記録に持っていく
    await ctx.db.prepare(`INSERT INTO works(user_id,work_key,title,first_date,last_date,times,verdict,chosen,note_impression,note_motive,stage_id,time,updated_at)
      VALUES(?,?,?,?,?,1,NULL,NULL,'',?,?,?,?) ON CONFLICT(user_id,work_key) DO NOTHING`)
      .bind(ctx.uid, key, m.title, t.date, t.date, react.get(t.sid)?.note_pre || '', t.sid, t.time || '', nowIso(ctx)).run();
  }
}

/** app._rebucket for the three lists: {tracking, favourites, owned, others, declined, react, tickets}. */
export async function buckets(ctx, {catalogue = false} = {}) {
  await promoteOwned(ctx);
  const [react, tickets, declared, words] = await Promise.all([reactionsOf(ctx), ticketsOf(ctx), loadDeclared(ctx), loadDeclined(ctx)]);
  const {hits, declined} = await nameHits(ctx, declared, words, {catalogue});
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
  const out = {tracking: [], favourites: [], favOwned: [], owned: [], others: [], react, tickets, declared, words, declined, hits};
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
    const row = {...(group.find(v => v.stage_id === pick) || m), sids, prefs: [...new Set(group.map(v => v.pref).filter(Boolean))], note: react.get(pick)?.note || '', note_pre: pre, src: react.get(pick)?.src || '',
      why: sids.map(s => react.get(s)?.why).find(Boolean) || null,
      at: sids.map(x => react.get(x)?.at || '').sort().at(-1) || ''};
    if (r.owned === 1) {
      seen.add(key);
      const done = doneDate(sids, row.end, tickets);
      if (startPassed(done.date, done.time, ctx)) continue;
      out.owned.push(row);
      // お気に入りの名前に当たる公演は、購入済みにしてもお気に入りの画面に残す（印を付けて。favOwned）。
      // 起案者の指示（2026-10-15）「購入済み押してもお気に入りから消さないで」。カレンダー・開幕リマインドは
      // 購入済みとして 1 回だけ出すので、favourites には入れない。
      const fav = sids.find(s => hits.has(s));
      if (fav) out.favOwned.push({...row, stage_id: fav, a: hits.get(fav).a, owned: true});
    } else if (r.interest === 1) { seen.add(key); out.tracking.push(row); }
    else if (r.interest === 0) { seen.add(key); out.others.push(row); }
    else if (r.interest === 2) { seen.add(key); out.others.push({...row, cantgo: true}); }   // 行けない
    // ✕ で候補から消した公演（3: おすすめ・お気に入りなどで、4: 興味ありの画面で）は、どの一覧にも出さない（お気に入りの名前に
    // 当たっていても。起案者の指示 2026-10-18「お気に入りとか、これいらんなってときがある。その時候補から消したい」）
    else if (r.interest === 3 || r.interest === 4) { seen.add(key); out.others.push({...row, dismissed: true}); }
    else if (hits.has(m.stage_id)) { seen.add(key); out.favourites.push({...row, stage_id: m.stage_id, a: hits.get(m.stage_id).a}); }
  }
  const byStart = (a, b) => cmp(a.start || '9999', b.start || '9999');
  out.tracking.sort(byStart);
  out.favourites.sort(byStart);
  return out;
}

// 並べ替え（起案者の指示 2026-10-15「今どのページも上演日の近い順に並べてるけど、それ以外の並べ替えをプルダウンで
// 選べるようにできる？規定は近い順でいい」）。興味あり・お気に入り・購入済み公演で同じ選択肢を使う（?s=）。
export const SORTS = {start: '上演日の近い順', end: '楽日の近い順', added: '追加した新しい順', title: '公演名順', pref: '都道府県順'};
const JA = new Intl.Collator('ja');
const prefIdx = p => (PREFS.includes(p) ? PREFS.indexOf(p) : PREFS.length);
export function sortRows(rows, key) {
  const byStart = (a, b) => cmp(a.start || '9999', b.start || '9999') || cmp(a.stage_id, b.stage_id);
  const f = {
    start: byStart,
    end: (a, b) => cmp(a.end || '9999', b.end || '9999') || byStart(a, b),
    added: (a, b) => cmp(b.at || '', a.at || '') || byStart(a, b),
    title: (a, b) => JA.compare(a.title || '', b.title || '') || byStart(a, b),
    pref: (a, b) => (prefIdx(a.pref) - prefIdx(b.pref)) || byStart(a, b),
  }[key] || byStart;
  return [...rows].sort(f);
}
const sortOf = (params, keys) => { const k = params.get('s') || 'start'; return keys.includes(k) ? k : 'start'; };
/** The 並べ替え pull-down (a GET form: app.js turns it into a screen change). */
function sortForm(action, sort, keys, keep = '') {
  const opts = keys.map(k => `<option value="${k}"${k === sort ? ' selected' : ''}>${E(SORTS[k])}</option>`).join('');
  return `<form class="sortf" method="get" action="${action}"><input type="hidden" name="t" value="__TAGURI_TOKEN__">${keep}`
    + `<label>並べ替え <select name="s" data-autosubmit>${opts}</select></label>`
    + '<noscript><button type="submit">並べ替える</button></noscript></form>';
}
const monthKey = r => (r.start || '').slice(0, 7);
const monthLabel = m => { const [y, mo] = m.split('-'); return mo ? `${y} 年 ${Number(mo)} 月` : '上演日が分からない公演'; };
/** render_recommend.month_pick */
export function monthPick(rows, sel, page, action, sort = 'start', keep = '', {allLine = true} = {}) {
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
  const url = (m, pg) => link + (m ? `&amp;m=${E(m)}` : '') + (pg > 1 ? `&amp;p=${pg}` : '') + (sort !== 'start' ? `&amp;s=${E(sort)}` : '') + keep;
  const tabs = indexTabs([['', 'すべて', rows.length], ...months.map(m => [m, monthLabel(m === 'none' ? '' : m), counts[m]])],
    sel, m => url(m, 1), '月で切り替える');
  const where = !sel ? E(SORTS[sort] || SORTS.start) : `<b>${E(monthLabel(sel === 'none' ? '' : sel))}</b>の ${hit.length} 件`;
  const first = (page - 1) * LIST_TOP + 1;
  const now = hit.length <= LIST_TOP ? `${where}で、${hit.length} 件すべてを表示しています。`
    : `${where}の <b>${first}〜${first + show.length - 1} 件目</b>を表示しています（全 ${hit.length} 件）。<b>残りは下の「次の ${LIST_TOP} 件」か、上の月のタブから見られます。</b>`;
  // お気に入りでは、全部が 1 ページに収まるときの 1 行（「上演日の近い順で、1 件すべてを表示しています。」）を出さない
  // （起案者の指示 2026-10-18「削除」）。ページに分かれるときの案内は残す
  const head = `${tabs}<div class="idxsheet loose">${allLine || hit.length > LIST_TOP ? `<p class="mnow">${now}</p>` : ''}`;
  if (last <= 1) return [show, head, '</div>'];
  const prev = page > 1 ? `<a class="mpage" href="${url(sel, page - 1)}">← 前の ${LIST_TOP} 件</a>` : '<span class="mpage off">最初のページです</span>';
  const nxt = page < last ? `<a class="mpage" href="${url(sel, page + 1)}">次の ${Math.min(LIST_TOP, hit.length - page * LIST_TOP)} 件 →</a>` : '<span class="mpage off">これで最後です</span>';
  return [show, head, `</div><div class="mfoot">${prev}<span class="mp">${page} / ${last} ページ</span>${nxt}</div>`];
}

/** Filled cards for these rows in one list. */
async function cards(ctx, rows, mode, extra = () => ({})) {
  const {html, posters} = await cardTemplates(ctx.db, rows.map(r => r.stage_id));
  const bare = rows.map(r => r.stage_id).filter(sid => !html.has(sid));
  // お気に入り says why each stage is there (the registered name), as its prebuilt cards do.
  if (bare.length) for (const [sid, s] of await stageInfo(ctx.db, bare)) html.set(sid, fallbackTemplate(s, {why: mode === 'favourite'}));
  // 興味あり・お気に入り・購入済みの一覧も、おすすめと同じ日程（会場ごとの行・公演日時の暦・会場で違う料金）にする
  // （起案者の指示 2026-10-17「お気に入りページにまだ『このおすすめの日程』が生き残ってるので他のページと揃えて」）
  const info = ['interest', 'favourite', 'owned'].includes(mode) ? await stageInfo(ctx.db, rows.flatMap(r => r.sids || [r.stage_id])) : null;
  return rows.filter(r => html.has(r.stage_id)).map(r => {
    const pic = posters.get(r.stage_id) || r.sids?.map(s => posters.get(s)).find(Boolean);
    let card = compose(html.get(r.stage_id), r.stage_id, mode, {poster: pic ? posterHtml(pic) : '', ...extra(r)});
    // 興味あり・購入済のカードは共有できる（dec-share-links）。compose は Python の build_cards と同じ形のままにする
    if (mode === 'interest' || mode === 'owned') card = withShareButton(card, shareStageButton(r.stage_id, mode));
    if (!info) return card;
    const sids = [...new Set([r.stage_id, ...(r.sids || [])].map(String))];
    return withTour(card, tourBlock(sids.map(s => info.get(s)).filter(Boolean), r.stage_id, ctx.today, ctx.prefs || []));
  });
}
const qInt = (params, k) => Math.max(1, Number.parseInt(params.get(k) || '1', 10) || 1);

// 興味ありを押した画面が、おすすめ以外のとき、おすすめ理由の欄の代わりに出す言葉（起案者の指示 2026-10-15
// 「開幕リマインドから追加したものは、おすすめ理由という欄ではなく、「開幕リマインドからの追加」だけ書いて」）
const ORIGIN = {reminder: '開幕リマインドからの追加', search: '探すからの追加'};
/**
 * 理由を残す前に押した興味ありの理由（おすすめの控えの answered_why）。興味ありの公演は自分も種になっているので、
 * 作品名から自分の題名を除き、自分のほかに作品が無い人と種類は理由から外す。
 */
export function ownlessWhy(w, title) {
  const titles = new Map((w.titles || []).map(([k, v]) => [k, (v || []).filter(t => t !== title)]));
  const via = new Map([...(w.via || []), ...(w.fav || [])]);   // お気に入りの名前で書く人（fav）も、作品名が無くても残す
  const keep = p => { const k = p[1] + '\t' + p[2]; return via.has(k) || (titles.get(k) || []).length > 0; };
  return {...w, parts: w.parts.filter(keep), kinds: w.kinds.filter(keep), titles: [...titles]};
}

/** 興味ありの各行のおすすめ理由（押したときに残したもの、無ければ今のおすすめの控えから。どちらも無ければ空） */
async function interestWhy(ctx, show) {
  const out = new Map();
  for (const r of show) if (r.why) out.set(r.stage_id, reasonRows(r.why, new Map(r.why.titles || [])));
  const rest = show.filter(r => !r.why && !ORIGIN[r.src]);
  if (!rest.length) return out;
  const data = await rankedGroups(ctx);
  const ans = new Map(data.answered_why || []);
  for (const r of rest) {
    const w = [r.stage_id, ...(r.sids || [])].map(s => ans.get(s)).find(Boolean);
    if (!w) continue;
    const o = ownlessWhy(w, r.title);
    if (o.parts.length || o.kinds.length) out.set(r.stage_id, reasonRows(o, new Map(o.titles)));
  }
  return out;
}

export async function interestScreen(params, ctx) {
  const b = await buckets(ctx);
  const keys = ['start', 'end', 'added', 'title', 'pref'], sort = sortOf(params, keys);
  const rows = sortRows(b.tracking, sort);
  const [show, mfil, mfoot] = monthPick(rows, params.get('m') || '', qInt(params, 'p'), '/recommend/interest', sort);
  const whys = rows.length ? await interestWhy(ctx, show) : new Map();
  const list = rows.length
    ? `<p class="lead"><b>${E(SORTS[sort])}</b>に並んでいます。順位は付けていません。</p><div class="tickets">`
      + (await cards(ctx, show, 'interest', r => ({note: r.note, origin: ORIGIN[r.src] || '', why: whys.get(r.stage_id) || ''}))).join('') + '</div>'
    // 0 件のときは、おすすめの初めてのワンポイントと同じ形の、絵の付いた案内（起案者の指示 2026-10-18 の文面）
    : emptyGuide('interest', '「興味あり」の公演はまだありません', '<p>「<a href="/recommend?t=__TAGURI_TOKEN__">おすすめ</a>」または「<a href="/recommend/reminder?t=__TAGURI_TOKEN__">開幕リマインド</a>」、'
      + '「<a href="/search?t=__TAGURI_TOKEN__">探す</a>」で「興味あり」と回答してください。</p>');
  // 見出しは「「興味あり」の公演」（起案者の指示 2026-10-18。以前は「追いかけている N 件」）。
  // 0 件のときは月のタブと「0 件すべてを表示しています」を出さず、案内だけにする。「並べ替え」はお気に入りと同じく年月のタブより下
  // （起案者の答え 2026-10-18「お願い」）
  const body = `<h1>「興味あり」の公演</h1>
<p class="lede">「興味あり」を押した公演を並べています。順位は付けていません。並べ替えは下の「並べ替え」で選べます。チケットが取れたら「すでに持っている」を押してください。「購入済の公演」に移り、上演日を過ぎると評価待ちに並びます。<br>
「なぜ気になったか」に書いた名前は、<a href="/recommend/favourites?t=__TAGURI_TOKEN__">お気に入り</a>に加える候補として並びます。</p>
${rows.length ? mfil : ''}
${rows.length ? sortForm('/recommend/interest', sort, keys, params.get('m') ? `<input type="hidden" name="m" value="${E(params.get('m'))}">` : '') : ''}
${list}
${rows.length ? mfoot : ''}`;
  return {title: '興味あり', body_html: body};
}

const KIND_OFF_LABEL = {'#形式': '形式', '#原作': '原作', '#翻訳': '翻訳', '#原作の国': '原作の国', '#会場': '劇場', '#題材': '題材', '#ジャンル': 'ジャンル'};
/** 「使わない」にした種類の理由の一覧（q-kind-reason-off）。1 つも無いときは出さない */
export function kindOffBox(keys) {
  if (!keys.length) return '';
  const tags = keys.map(k => {
    const [axis, tag] = k.split('\t');
    const label = KIND_OFF_LABEL[axis] || axis.replace(/^#+/, '');
    return `<span class="tag" data-kindkey="${E(k)}">${tag.endsWith(label) ? '' : E(label)}「${E(tag)}」<button data-kindoff-remove="1">✕</button></span>`;
  }).join('');
  return `<details class="pbox" id="kind-off">
<summary>${ico('flag')}使わない理由 <b>${keys.length}件</b></summary>
<p class="lead">「おすすめ理由」の ✕ で外した要素です。</p>
<div class="tags">${tags}</div>
</details>`;
}

/**
 * 設定の画面の「外したおすすめ理由」（起案者の指示 2026-10-21「間違って✕で消しちゃったオススメ理由を復活させたい。設定ページに追加」）。
 * 理由の ✕ は、人物の行なら「使わない言葉」（declined）に、形式の行なら「使わない理由」（kind_off）に入る。ここから 1 つずつ戻す。
 * 戻す押し口は app.js の既存の道（.tag の data-dec="remove" と data-kindoff-remove）をそのまま使う。読み出しは 2 行（app_setting）。
 */
export function reasonOffCardHtml(words, kindKeys, summary) {
  const label = k => (DEC_KINDS.find(([v]) => v === k) || ['', ''])[1];
  const wtags = words.map(e => {
    const {kind, word} = decEntry(e);
    return `<span class="tag" data-word="${E(e)}">${kind ? E(label(kind)) : ''}「${E(word)}」<button data-dec="remove">戻す</button></span>`;
  }).join('');
  const ktags = kindKeys.map(k => {
    const [axis, tag] = k.split('\t');
    const kl = KIND_OFF_LABEL[axis] || axis.replace(/^#+/, '');
    return `<span class="tag" data-kindkey="${E(k)}">${tag.endsWith(kl) ? '' : E(kl)}「${E(tag)}」<button data-kindoff-remove="1">戻す</button></span>`;
  }).join('');
  const n = words.length + kindKeys.length;
  return `<details class="card" id="reason-off">${summary(n)}
<p class="lead">おすすめの「なぜ出てきたか」で ✕ を押して外した理由です。<b>「戻す」を押すと、次の組み直しから、また理由とおすすめに使います。</b></p>
${n ? '' : '<p class="empty">外した理由はありません。</p>'}
${words.length ? `<h3>人物・言葉（使わない言葉）</h3>
<p class="lead">人物の ✕ で外した名前と、自分で足した「使わない言葉」です。その言葉が入った公演は、おすすめに出ません。</p>
<div class="tags">${wtags}<span class="said"></span></div>` : ''}
${kindKeys.length ? `<h3>形式・原作など（使わない理由）</h3>
<p class="lead">理由として使わないだけで、公演はおすすめに出ます。</p>
<div class="tags">${ktags}<span class="said"></span></div>` : ''}
</details>`;
}

export function declinedBox(words) {
  const label = k => (DEC_KINDS.find(([v]) => v === k) || ['', ''])[1];
  const tags = words.map(e => {
    const {kind, word} = decEntry(e);
    return `<span class="tag" data-word="${E(e)}">${kind ? `${E(label(kind))}` : ''}「${E(word)}」<button data-dec="remove">✕</button></span>`;
  }).join('');
  const kinds = DEC_KINDS.map(([v, t]) => `<option value="${E(v)}">${E(t)}</option>`).join('');
  return `<details class="pbox" id="declined">
<summary>${ico('flag')}使わない言葉 <b>${words.length}語</b></summary>
<p class="lead">おすすめに表示しない言葉を設定できます。</p>
${words.length ? tags : '<p class="empty">まだ 1 つも外していません。</p>'}
<div class="fav-add"><select id="dec-kind" aria-label="使わない言葉の対象">${kinds}</select> <input id="dec-word" type="text"
  placeholder="使わない言葉（例: バレエ）" size="22">
 <button data-dec="add">追加する</button><span class="said"></span></div>
</details>`;
}

/**
 * お気に入りのハッシュタグを押したときの画面（?n=名前）。起案者の指示（2026-10-15）「押したらその絞り込みみたいなの
 * できたらいいけど（その人名が登録されてる公演（過去も含め）が全部表示されるとか）」。
 * - これからの公演: お気に入りの一覧のうち、その名前で当たったもの（カードの形）。
 * - 観た公演: 自分の記録のうち、出演・作り手にその名前がある（名前全体で一致）か、題名・団体に含むもの。
 * - 過去の公演（2019 年以降の一覧 past_stage）: 一覧を全部読むので（D1 の読み取り行数）、押したときだけ探す。
 */
const PAST_SCANS_PER_DAY = 150;           // 150 × 2 万行 = 300 万行（1 日 500 万行の 6 割）
// 1 人が 1 日に使える分（issue #73「1 人で使い切れる」）。全体の 150 回を、ほかの人にも残す
export const PAST_SCANS_PER_USER_DAY = 20;
/**
 * 今日の過去の公演の検索が上限の内なら数えて true（rec_meta 'past_scan' = "YYYY-MM-DD n"）。
 * 1 人ずつの数は usage の 'pastscan:<日>:<日と利用者のハッシュ>'（利用者の ID そのものは書かない）。前の日の行は消す。
 */
export async function takePastScan(ctx) {
  const row = await ctx.db.prepare("SELECT v FROM rec_meta WHERE k='past_scan'").first().catch(() => null);
  const [day, n] = String(row?.v || '').split(' ');
  const used = day === ctx.today ? Number(n) || 0 : 0;
  if (used >= PAST_SCANS_PER_DAY) return false;
  const digest = new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(`${ctx.today}|${ctx.uid}`)));
  const mine = `pastscan:${ctx.today}:${[...digest.slice(0, 12)].map(b => b.toString(16).padStart(2, '0')).join('')}`;
  const own = (await ctx.db.prepare('SELECT n FROM usage WHERE k=?').bind(mine).first().catch(() => null))?.n || 0;
  if (own >= PAST_SCANS_PER_USER_DAY) return false;
  await ctx.db.batch([
    ctx.db.prepare("INSERT INTO rec_meta(k,v) VALUES('past_scan',?) ON CONFLICT(k) DO UPDATE SET v=excluded.v").bind(`${ctx.today} ${used + 1}`),
    ctx.db.prepare("DELETE FROM usage WHERE k LIKE 'pastscan:%' AND k<?").bind(`pastscan:${ctx.today}`),
    ctx.db.prepare('INSERT INTO usage(k,n) VALUES(?,1) ON CONFLICT(k) DO UPDATE SET n=n+1').bind(mine)]);
  return true;
}
const slash = d => String(d || '').replaceAll('-', '/');
/**
 * 過去の公演（2019 年以降の一覧）のうち、出演・作り手に名前全体が一致するか、団体に含むもの。
 * ツアーは会場ごとに分けず 1 行にまとめる（起案者の指示 2026-10-15「ツアーでも地方ごとに表示せず、ひとまとめにして記載」）:
 * 題名の鍵（tkey）と団体が同じ行を 1 つにし、期間は最初の初日〜最後の楽日、会場は「A ほか N 会場」。
 */
/** deliver_past_index.shard_of: FNV-1a (32 bit) of the UTF-8 bytes of the normalised name, modulo 256. */
export function pastShard(key) {
  let h = 0x811c9dc5;
  for (const b of new TextEncoder().encode(key)) { h ^= b; h = Math.imul(h, 0x01000193) >>> 0; }
  return h % 256;
}
/**
 * 名前の索引（R2 の pastidx/v1/<shard>.json、毎日の取得が deliver_past_index.py で置く）から、その名前の過去の公演を読む。
 * R2 の読み出し 1 回で済み、D1 は読まない（docs/knowledge: dec-past-name-index）。索引がまだ無い・R2 が使えないときは null。
 */
export async function pastFromIndex(ctx, key) {
  const bucket = ctx.env?.POSTERS;
  if (!bucket) return null;
  try {
    if (!(await r2ReadAllowed(ctx.env))) return null;
    const obj = await bucket.get(`pastidx/v1/${pastShard(key).toString(16).padStart(2, '0')}.json`);
    if (!obj) return null;
    const j = await obj.json();
    return (j?.names?.[key] || []).map(sid => {
      const r = j.stages?.[sid] || [];
      return {stage_id: String(sid), title: r[0] || '', tkey: r[1] || '', start: r[2] || '', end: r[3] || '', venue: r[4] || '', grp: r[5] || ''};
    }).filter(r => r.title);
  } catch { return null; }
}
/** 索引が届く前の代わり: past_stage を全部読む（1 回で最大 2 万行）。全体で 1 日 PAST_SCANS_PER_DAY 回まで。 */
async function pastFromScan(ctx, name, key) {
  if (!await takePastScan(ctx)) return null;
  const raw = String(name).replace(/[\s　]+/gu, '');
  let rows = [];
  try {
    ({results: rows} = await ctx.db.prepare('SELECT stage_id,title,tkey,start,end,venue,grp,pref,people FROM past_stage WHERE instr(people,?)>0 OR instr(grp,?)>0 ORDER BY start DESC LIMIT 500')
      .bind(raw, raw).all());
  } catch { rows = []; }
  return rows.filter(r => {
    let ps = [];
    try { ps = JSON.parse(r.people || '[]'); } catch { /* no credits */ }
    return ps.some(([, n]) => nz(n) === key) || nz(r.grp).includes(key);
  });
}
async function pastByName(ctx, name, key, seenSids) {
  const rows = (await pastFromIndex(ctx, key)) ?? (await pastFromScan(ctx, name, key));
  if (rows === null) return '<p class="empty">過去の公演の索引がまだ届いていません。代わりの検索も今日の回数の上限に達しました。索引は毎日の取得のあとに届きます。</p>';
  const hit = rows.filter(r => !seenSids.has(String(r.stage_id)) && r.end && r.end < ctx.today);
  const groups = new Map();
  for (const r of hit) {
    const k = (r.tkey || nz(r.title)) + '\u0000' + nz(r.grp);
    if (!groups.has(k)) groups.set(k, []);
    groups.get(k).push(r);
  }
  const prod = [...groups.values()].map(g => {
    const start = g.map(r => r.start).filter(Boolean).sort()[0] || '', end = g.map(r => r.end).filter(Boolean).sort().at(-1) || '';
    const venues = [...new Set([...g].sort((a, b) => cmp(a.start, b.start)).map(r => r.venue).filter(Boolean))];   // 初日の早い会場から
    return {title: g[0].title, grp: g[0].grp, start, end, where: venues.length > 1 ? `${venues[0]} ほか ${venues.length - 1} 会場` : (venues[0] || '')};
  }).sort((a, b) => cmp(b.start, a.start));
  if (!prod.length) return '<p class="empty">過去の公演の一覧には見つかりませんでした。この一覧は 2019 年以降の公演で、毎日少しずつ増えています。</p>';
  return '<ul class="nmlist">' + prod.map(r => `<li><span class="d">${E(slash(r.start))}${r.end && r.end !== r.start ? `〜${E(slash(r.end).slice(5))}` : ''}</span>`
    + `<span class="t">${E(r.title)}</span><span class="w">${E([r.grp, r.where].filter(Boolean).join('／'))}</span></li>`).join('') + '</ul>';
}

/** ツアーのカードを 1 つにまとめる: 期間を全会場の最初〜最後にし、地方ごとの日程の欄と「〇〇公演の日程」を出さない。 */
export async function wholeTour(ctx, html, rows) {
  const multi = rows.filter(r => (r.sids || []).length > 1);
  if (!multi.length) return html;
  const info = await stageInfo(ctx.db, multi.flatMap(r => r.sids));
  const md = d => `${Number(d.slice(5, 7))}/${Number(d.slice(8, 10))}`;
  const byStage = new Map(multi.map(r => [String(r.stage_id), r]));
  return html.map(h => {
    const sid = (/data-stage="([^"]+)"/.exec(h) || [])[1];
    const r = byStage.get(sid);
    if (!r) return h;
    const ss = r.sids.map(x => info.get(x)).filter(Boolean);
    const lo = ss.map(x => x.start).filter(Boolean).sort()[0], hi = ss.map(x => x.end).filter(Boolean).sort().at(-1);
    let out = h.replace(/ data-tour="[^"]*"/, '');
    if (lo && hi) {
      const state = lo > ctx.today ? '' : hi >= ctx.today ? '上演中' : '終了';
      out = out.replace(/ data-range="[^"]*" data-state="[^"]*"/, ` data-range="${md(lo)}〜${md(hi)}" data-state="${state}"`);
    }
    // 地方ごとの日程の欄（.tourfull、中に .tf-row の div が並ぶ）を外す
    const i = out.indexOf('<div class="tourfull">');
    if (i >= 0) {
      const tag = /<(\/?)div\b[^>]*>/g;
      tag.lastIndex = i;
      let depth = 0, m;
      while ((m = tag.exec(out))) { depth += m[1] ? -1 : 1; if (!depth) { out = out.slice(0, i) + out.slice(m.index + m[0].length); break; } }
    }
    return out;
  });
}

async function nameView(params, ctx, b, name) {
  const key = nz(name);
  const label = r => (/「(.*)」$/.exec(r) || [, r])[1];
  const favs = sortRows([...b.favourites, ...b.favOwned].filter(r => r.a.some(x => nz(label(x)) === key)), 'start');
  const why = r => ({owned: Boolean(r.owned), tags: [...new Set(r.a.map(label))]});
  const up = favs.length ? `<div class="tickets">${(await wholeTour(ctx, await cards(ctx, favs, 'favourite', why), favs)).join('')}</div>`
    : '<p class="empty">今後の公演はいまのところ見つかっていません。</p>';
  // 観た公演
  const ws = (await loadWorks(ctx)).filter(w => !w.unseen);
  const people = await peopleByKey(ctx, ws);
  const seenRows = ws.filter(w => (people[w.work_key] || []).some(([, n]) => nz(n) === key)
    || nz(w.title).includes(key) || nz(w.group || '').includes(key))
    .sort((p, q) => cmp(q.first_date || '', p.first_date || ''));
  const seenSids = new Set(seenRows.map(w => w.stage_id).filter(Boolean));
  const seen = seenRows.length ? '<ul class="nmlist">' + seenRows.map(w => `<li><span class="d">${E((w.first_date || '').replaceAll('-', '/'))}</span>`
    + `<span class="t">${E(w.title)}</span>${w.verdict ? `<span class="v">${E(gradeText(w.verdict))}</span>` : ''}</li>`).join('') + '</ul>'
    : '<p class="empty">観た公演の記録には、この名前は見つかりませんでした。</p>';
  // 過去の公演: 開いたときに自動で出す（起案者の指示 2026-10-15「過去の公演はボタン押して調べるんじゃなくて自動的に表示して」
  // 「明日じゃ困る。すぐ表示できるための方法考えて」）。名前の索引（R2）を 1 回読むだけ。索引が届く前は past_stage を読む（回数に上限）
  const past = await pastByName(ctx, name, key, seenSids);
  const body = `<h1><span class="ftag big">#${E(name)}</span> の公演</h1>
<p class="lede"><a href="/recommend/favourites?t=__TAGURI_TOKEN__">← お気に入りに戻る</a></p>
<h2>今後の公演 <span class="cnt">${favs.length} 件</span></h2>
${up}
<h2>観た公演 <span class="cnt">${seenRows.length} 件</span></h2>
${seen}
<h2>過去の公演 <span class="cnt">2019 年以降</span></h2>
${past}`;
  return {title: `#${name}`, body_html: body};
}

export async function favouritesScreen(params, ctx) {
  const b = await buckets(ctx, {catalogue: true});
  const named = String(params.get('n') || '').trim().slice(0, 80);
  if (named) return nameView(params, ctx, b, named);
  const nCat = Number((await ctx.db.prepare("SELECT v FROM rec_meta WHERE k='catalogue_upcoming'").first().catch(() => null))?.v || 0);
  const keys = ['start', 'end', 'title', 'pref'], sort = sortOf(params, keys);
  // 場所の絞り込みは結果の絞り込み（起案者の指摘 2026-10-17）。そのページの中だけで効き、既定は設定の県
  const prefs = await prefsFor(params, ctx);
  ctx.prefs = prefs;   // ツアーの日程で、絞り込んだ県の会場に ★（schedule.tourBlock）
  const prefsOf = r => (r.prefs && r.prefs.length ? r.prefs : [r.pref].filter(Boolean));
  const allFavs = sortRows([...b.favourites, ...b.favOwned], sort), dec = b.declared;
  const pcounts = {};
  for (const r of allFavs) for (const p of new Set(prefsOf(r))) pcounts[p] = (pcounts[p] || 0) + 1;
  const favs = prefs.length ? allFavs.filter(r => prefsOf(r).some(p => prefs.includes(p))) : allFavs;
  const [show, mfil, mfoot] = monthPick(favs, params.get('m') || '', qInt(params, 'p'), '/recommend/favourites', sort, prefQs(params), {allLine: false});
  const kinds = KINDS.map(k => `<option value="${E(k)}">${E(k)}</option>`).join('');
  // 登録した名前は、カードの中のハッシュタグ（.ftag）と同じ形で並べる（起案者の指示 2026-10-17「お気に入りに登録したときの
  // 『足す外す』の欄のデザイン、本文カード内のハッシュタグのデザインと合わせて」）。押すとその名前の公演の画面へ
  const roleOf = await loadRoles(ctx);
  const tags = KINDS.flatMap(k => (dec[k] || []).map(n => `<span class="tag ftag" data-kind="${E(k)}" data-name="${E(n)}">`
    // 札は「#人「人名」」の形（起案者の指示 2026-10-18「『#人名 人』→『#人「人名」』」。団体・作品・題材なども同じ形）
    // 役職で絞った人は、札の後ろに選んだ役職を添える（q-favourite-homonym）
    + `<a class="tgn" href="/recommend/favourites?t=__TAGURI_TOKEN__&amp;n=${encodeURIComponent(n)}">#${E(k)}「${E(n)}」${k === '人' && roleOf[n] ? `<small class="frole">${E(roleOf[n].join('・'))}</small>` : ''}</a>`
    + `<button data-fav="remove" aria-label="「${E(n)}」を外す">✕</button></span>`)).join('');
  const keep = !allFavs.length;
  const n = KINDS.reduce((s, k) => s + (dec[k] || []).length, 0);
  // 登録した名前は、この一覧に出る公演そのものを決める。場所・料金は出てきた公演の絞り込み。2 段に分ける
  // （起案者の指示 2026-10-17。出さない語・使わない理由はおすすめの設定なので、おすすめの画面に置く）
  const tools = `<p class="fgh">${ico('star', 15)}<b>お気に入りに出す名前</b><span>お気に入りに表示される結果自体が変わります。</span></p>`
    + `<div class="fil2 tune"><details class="pbox" id="names"${keep ? ' open' : ''}>`
    // 見出しと説明の文は起案者の指示 2026-10-18（「登録した名前」→「要素を登録」、説明は表記ゆれの 1 文だけ）
    + `<summary>${ico('star')}要素を登録 <b>${n}件</b> ── 足す・外す</summary>`
    + '<p class="lead">表記ゆれ（漢字とカタカナ、送り仮名の違いなど）は、自動では見分けられない場合があります。</p>'
    + `<div class="fav-add"><label class="fld" for="fav-kind"><span class="fl">種類<small class="req">必須</small></span><select id="fav-kind">${kinds}</select></label> <label class="fld" for="fav-name"><span class="fl">名前<small class="req">必須</small></span><input id="fav-name" type="text" placeholder="例：劇団四季・シェイクスピア・家族" size="26"></label> <button data-fav="add">登録する</button>${favRoleBox()}`
    + `<span class="said"></span></div><div class="tags">${tags}</div></details></div>`
    + (allFavs.length ? `<p class="fgh">${ico('search', 15)}<b>表示の絞り込み</b><span>お気に入りの公演の中から、表示する項目を設定できます。</span></p>`
      + `<div class="fil2 narrow">${prefForm(pcounts, prefs, '/recommend/favourites', PAGE_PREF_NOTE, sort !== 'start' ? {s: sort} : {},
        regionCounts(allFavs.map(r => ({key: r.stage_id, prefs: prefsOf(r)}))))}</div>` : '');
  // 当たった名前（「人「俳優甲」」→「俳優甲」）をハッシュタグにする。理由の欄は出さない（起案者の指示 2026-10-15）
  const why = r => ({owned: Boolean(r.owned), tags: [...new Set(r.a.map(w => (/「(.*)」$/.exec(w) || [, w])[1]))]});
  const where = prefs.length <= 3 ? prefs.join('・') : `${prefs[0]}ほか ${prefs.length - 1} 県`;
  const list = !favs.length && allFavs.length
    ? `<p class="empty"><b>${E(where)}</b>で観られるお気に入りの公演はありません（全国では ${allFavs.length} 件）。ほかの都道府県を選ぶか、全国に戻してください。</p>`
    : favs.length
    // 並び方と「購入済みにする」の説明の段落は外した（起案者の指示 2026-10-18「削除」）
    ? `<div class="tickets">${(await cards(ctx, show, 'favourite', why)).join('')}</div>`
    : `<p class="empty">登録した名前に当たる公演は、いまたぐりが集めている公演${nCat ? `（CoRich・ステイジーズカレンダーから毎日集めている、これからの公演 ${nCat} 件）` : ''}の中にはありません。<b>当たる公演が新しく集まると、毎日の更新のあとにここに出ます。</b>表記ゆれ（漢字とカタカナなど）があるときは、別の書き方も登録してみてください。</p>`;
  // 件数の 1 行は、おすすめと同じく枠に入れず、表示の絞り込みの下に地の文で（起案者の指示 2026-10-18「他ページにも反映して」）
  const rcount = allFavs.length ? `<p class="rcount"><b>${prefs.length ? E(where) : '全国'}</b>／全 ${allFavs.length} 件中 ${favs.length} 件を表示中</p>` : '';
  // 見出しは「お気に入り」だけにし、下に何をする画面かを 1 文で（起案者の指示 2026-10-18 の文面）。
  // 「並べ替え」は年月で絞り込むタブより下に置く（同じ指示）。1 文は見出しの下に見えるよう、ⓘ に移る p.lede ではなく p.hsub
  // 名前を 1 件も登録していないときは、名前の欄の下にイラスト付きの案内を出し、年月の絞り込み（「すべて」）・並べ替え・一覧は出さない
  // （起案者の指示 2026-10-19「お気に入りが１件もないときは…アイコンイラストを使ってそのことをわかりやすく説明（お気に入りに出す名前の
  // 入力欄の下）。文章は『お気に入りに登録されている要素がありません。』。お気に入りがないときは『すべて』の絞り込みを非表示」）
  if (!n) return {title: 'お気に入り', body_html: `<h1>お気に入り</h1>
<p class="hsub">おすすめにかかわらず新着情報を知りたい題材や作り手がいるときは、お気に入りに追加することで情報の追跡ができます。</p>
${tools}
${emptyGuide('favourite', 'お気に入りに登録されている要素がありません。', '<p>上の「要素を登録」で、劇団・俳優・演出家・作品・原作者・題材などの名前を登録すると、その名前の公演をここに並べます。</p>')}`};
  const body = `<h1>お気に入り${sharePageButton('favourites')}</h1>
<p class="hsub">おすすめにかかわらず新着情報を知りたい題材や作り手がいるときは、お気に入りに追加することで情報の追跡ができます。</p>
${tools}
${rcount}
${mfil}
${favs.length ? sortForm('/recommend/favourites', sort, keys, prefHidden(params)) : ''}
${list}
${mfoot}`;
  return {title: 'お気に入り', body_html: body};
}

export async function ticketsScreen(params, ctx) {
  const b = await buckets(ctx);
  const keys = ['start', 'end', 'added', 'title', 'pref'], sort = sortOf(params, keys);
  const owned = sortRows(b.owned, sort);
  const mine = r => r.sids.flatMap(s => (b.tickets.get(s) || []).map(t => ({...t, sid: s})))
    .sort((p, q) => cmp(p.date, q.date) || cmp(p.time || '', q.time || ''));
  const html = (await cards(ctx, owned, 'owned', r => ({mytix: mytixHtml(r.stage_id, r.start, r.end, mine(r)) + preNote(r.stage_id, r.note_pre)}))).join('');
  // 見出しは「購入済の公演」（起案者の指示 2026-10-18。以前は「購入済み公演 ── N 件」）
  const body = `<h1>購入済の公演</h1>
<p class="lede">「すでに持っている」と答えた公演と、購入確認メールから見つかった公演を並べています。<b>この一覧に入っても、次のおすすめは変わりません。</b>上演日を過ぎると一覧から外れ、<a href="/rate?t=__TAGURI_TOKEN__">評価一覧</a>の評価待ちに移ります。行く日は、各公演の「行く日」の欄から入れられます。</p>
${owned.length ? sortForm('/tickets', sort, keys) : ''}
${html || emptyGuide('owned', '購入済の公演はまだありません', '<p>「<a href="/recommend?t=__TAGURI_TOKEN__">おすすめ</a>」または「<a href="/recommend/reminder?t=__TAGURI_TOKEN__">開幕リマインド</a>」、'
  + '「<a href="/search?t=__TAGURI_TOKEN__">探す</a>」で「購入済」と回答してください。<br>また「<a href="/register?t=__TAGURI_TOKEN__">観劇記録を追加</a>」で購入済の公演を追加してください。</p>')}
`;
  return {title: '購入済の公演', body_html: body};
}

// ---------------------------------------------------------------- writes
/** serve.on_favourite (public user): add or remove a registered name. */
async function favouriteAction(b, ctx) {
  const action = String(b.action ?? ''), kind = String(b.kind ?? ''), name = String(b.name ?? '').trim().slice(0, 80);
  if (!['add', 'remove'].includes(action) || !KINDS.includes(kind) || !name) throw new ValueError('action（add / remove）・kind・name が要る');
  const v = await readJson(ctx, DECLARED_KEY);
  const d = Object.fromEntries(KINDS.map(k => [k, (v && Array.isArray(v[k]) ? v[k] : []).filter(x => typeof x === 'string')]));
  let cur = d[kind];
  // 外すときに無い名前なら書かない（保存の上限でも外す操作は通すので、行を増やさない。#88）
  const keep = action === 'remove' && !cur.includes(name);
  if (action === 'add') { if (!cur.includes(name)) cur.push(name); } else cur = cur.filter(x => x !== name);
  d[kind] = cur;
  // app.save_declared: trimmed, de-duplicated, sorted, at most 100 per kind.
  const out = Object.fromEntries(KINDS.map(k => [k, [...new Set(d[k].map(x => String(x).trim().slice(0, 80)).filter(Boolean))].sort(cmp).slice(0, 100)]));
  if (!keep) await writeJson(ctx, DECLARED_KEY, out);
  // 名前ごとに足した時刻（'種類\t名前' -> ISO）。再生（replay_eval）が日 t のお気に入りを組み立て直すのに使う（#72）。
  // 画面と推薦は読まない。足した名前・外した名前があるときだけ書く
  const at = await readJson(ctx, DECLARED_AT_KEY), stamps = at && typeof at === 'object' && !Array.isArray(at) ? at : {};
  const live = new Set(KINDS.flatMap(k => out[k].map(n => `${k}\t${n}`)));
  let moved = false;
  for (const e of Object.keys(stamps)) if (!live.has(e)) { delete stamps[e]; moved = true; }
  for (const e of live) if (!(e in stamps) && e === `${kind}\t${name}`) { stamps[e] = nowIso(ctx); moved = true; }
  if (moved) await writeJson(ctx, DECLARED_AT_KEY, stamps);
  if (action === 'remove') await ctx.db.prepare('DELETE FROM favourites WHERE user_id=? AND name=? AND kind=?').bind(ctx.uid, name, kind).run();
  // 人の役職の絞り（任意、q-favourite-homonym）。足すときに選んだ札で置き換え、選ばなければ絞りを外す。外すときも消す。
  // 変わらないときは書かない（D1 の書き込みを増やさない）
  let roles = [];
  if (kind === '人') {
    roles = action === 'add' && Array.isArray(b.roles) ? [...new Set(b.roles.map(String).filter(r => FAV_ROLE_OF.has(r)))] : [];
    roles.sort((x, y) => FAV_ROLES.findIndex(([l]) => l === x) - FAV_ROLES.findIndex(([l]) => l === y));
    const map = await loadRoles(ctx), was = JSON.stringify(map[name] || []);
    if (roles.length) map[name] = roles; else delete map[name];
    if (JSON.stringify(roles) !== was) await writeJson(ctx, ROLES_KEY, map);
  }
  return {body: {ok: true, kind, name, n: cur.length, ...(roles.length ? {roles} : {}),
    said: roles.length ? `登録しました（${roles.join('・')}として出ている公演だけ）。手元にある公演から探して、お気に入りに表示します`
      : '登録しました。手元にある公演から探して、お気に入りに表示します'}};
}

/** serve.on_decline (public user) */
async function declineAction(b, ctx) {
  const action = String(b.action ?? ''), kind = String(b.kind ?? '');
  // 外すときは控えの形（'対象\t語'）のまま届く。足すときは対象と語が別々に届く
  const raw = String(b.word ?? '').trim();
  const {kind: k0, word: w0} = decEntry(raw);
  const word = w0.trim().slice(0, 40);
  if (!['add', 'remove'].includes(action) || !word) throw new ValueError('action（add / remove）と word が要る');
  if (!DEC_KIND_SET.has(kind)) throw new ValueError('対象がおかしい');
  const entry = (k0 || kind) ? `${k0 || kind}\t${word}` : word;
  let cur = await loadDeclined(ctx);
  const keep = action === 'remove' && !cur.includes(entry);   // 無いものを外すときは書かない（#88）
  if (action === 'add') { if (!cur.includes(entry)) cur.push(entry); } else cur = cur.filter(w => w !== entry);
  cur = [...new Set(cur.map(w => w.trim().slice(0, 60)).filter(Boolean))].slice(0, 200);
  if (!keep) await writeJson(ctx, DECLINED_KEY, cur);
  return {body: {ok: true, word, kind: k0 || kind, n: cur.length}};
}

/** 種類の理由を「使わない」にする・戻す（q-kind-reason-off）。key は '#原作\tオリジナル' の形 */
async function kindOffAction(b, ctx) {
  const action = String(b.action ?? ''), key = String(b.key ?? '').trim().slice(0, 80);
  if (!['add', 'remove'].includes(action) || !/^#[^\t]+\t[^\t]+$/.test(key)) throw new ValueError('action（add / remove）と key（#種類 と 中身）が要る');
  let cur = await loadKindOff(ctx);
  const keep = action === 'remove' && !cur.includes(key);     // 無いものを外すときは書かない（#88）
  if (action === 'add') { if (!cur.includes(key)) cur.push(key); } else cur = cur.filter(k => k !== key);
  cur = [...new Set(cur)].slice(0, KIND_OFF_MAX);
  if (!keep) await writeJson(ctx, KIND_OFF_KEY, cur);
  return {body: {ok: true, key, n: cur.length}};
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
  actions: {favourite: favouriteAction, decline: declineAction, kind_off: kindOffAction, ticket: ticketAction},
};
