// Importing past performances from a Google Calendar or from ticket purchase
// mails (「公演情報の登録」①). The browser reads the calendar / mails itself
// (src/client/import-parse.js); these two writes only see what was read out.
//
// 起案者の指示（2026-10-14）「Google カレンダーから取り込みいいかも。メール取り込みも
// どうにか利用者の負担が少ない形で実現したい。購入サイトごとでもいい」
// (docs/knowledge: dec-import-calendar-mail).
//
// - POST /api/import_match {items: [{guesses: [title...], date}]}: which stage
//   each item is. Same rule as autolink: equal title key and the date inside
//   exactly one run. Items matching nothing come back without a stage; nothing
//   is stored.
// - POST /api/import_works {items: [{title, date, time, venue, stage_id}]}: the
//   ones the user ticked become records (as add_work does), skipping ones
//   already recorded.
import {titleKey} from './works.js';
import {pickStage, autoLink} from './autolink.js';
import {ValueError, localNow, slice, strip} from './py.js';
// The same day / time check as the browser's reader (and /api/record): no 2026-02-30, no 29:60.
import {isDay, isTime} from '../client/import-parse.js';

const MAX_ITEMS = 20;            // the request body is capped at 8 KB
const MAX_GUESSES = 4;
const PER_QUERY = 90;            // D1 binds at most 100 parameters
const STAGE_ID = /^[0-9A-Za-z_\-]{1,40}$/;

const text = (v, n) => slice(strip(typeof v === 'string' ? v : ''), 0, n).replace(/[\u0000-\u001f\u007f]/g, ' ');
function itemsOf(input) {
  const items = input.items;
  if (!Array.isArray(items) || !items.length) throw new ValueError('取り込むものがありません');
  if (items.length > MAX_ITEMS) throw new ValueError(`1 回に ${MAX_ITEMS} 件まで送れます`);
  return items.map(i => (i && typeof i === 'object' && !Array.isArray(i) ? i : {}));
}

/** title key -> [{stage_id, title, venue, start, end}] from past_stage and the current index. */
async function stagesByKey(db, keys) {
  const out = new Map();
  const add = r => {
    if (!out.has(r.tkey)) out.set(r.tkey, []);
    if (!out.get(r.tkey).some(s => s.stage_id === String(r.stage_id)))
      out.get(r.tkey).push({stage_id: String(r.stage_id), title: r.title, venue: r.venue || '', start: r.start || '', end: r.end || ''});
  };
  for (let i = 0; i < keys.length; i += PER_QUERY) {
    const part = keys.slice(i, i + PER_QUERY), qs = part.map(() => '?').join(',');
    const [past, cur] = await db.batch([
      db.prepare(`SELECT stage_id, title, tkey, venue, start, end FROM past_stage WHERE tkey IN (${qs})`).bind(...part),
      db.prepare(`SELECT stage_id, title, tkey, '' AS venue, start, end FROM rec_stage WHERE ver=(SELECT v FROM rec_meta WHERE k='current') AND tkey IN (${qs})`).bind(...part),
    ]);
    for (const r of past.results) add(r);
    for (const r of cur.results) add(r);
  }
  return out;
}

/** POST /api/import_match */
async function matchAction(input, ctx) {
  const items = itemsOf(input).map(i => ({
    date: isDay(i.date) ? i.date : '',
    keys: [...new Set((Array.isArray(i.guesses) ? i.guesses : []).slice(0, MAX_GUESSES)
      .map(g => titleKey(text(g, 200))).filter(k => Array.from(k).length >= 2))],
  }));
  const keys = [...new Set(items.flatMap(i => i.keys))];
  const byKey = keys.length ? await stagesByKey(ctx.db, keys) : new Map();
  const found = items.map(i => {
    for (const k of i.keys) {
      const sid = pickStage(byKey.get(k) || [], i.date);
      if (sid) return byKey.get(k).find(s => s.stage_id === sid);
    }
    return null;
  });
  // Already recorded: the same stage, or the same title key on that day.
  const sids = [...new Set(found.filter(Boolean).map(s => s.stage_id))];
  const wkeys = found.map((s, n) => s && items[n].date ? `${titleKey(s.title)}#${items[n].date}` : '').filter(Boolean);
  const have = new Set();
  for (let i = 0; i < Math.max(sids.length, wkeys.length); i += 40) {
    const a = sids.slice(i, i + 40), b = wkeys.slice(i, i + 40);
    const rows = (await ctx.db.prepare(`SELECT work_key, stage_id, first_date, last_date FROM works WHERE user_id=? AND (stage_id IN (${a.map(() => '?').join(',') || "''"}) OR work_key IN (${b.map(() => '?').join(',') || "''"}))`)
      .bind(ctx.uid, ...a, ...b).all()).results;
    for (const r of rows) {
      have.add(r.work_key);
      if (r.stage_id) have.add(`${r.stage_id}@${r.first_date}`).add(`${r.stage_id}@${r.last_date}`);
    }
  }
  return {body: {ok: true, items: found.map((s, n) => s
    ? {stage_id: s.stage_id, title: s.title, venue: s.venue, start: s.start, end: s.end,
       recorded: have.has(`${titleKey(s.title)}#${items[n].date}`) || have.has(`${s.stage_id}@${items[n].date}`)}
    : {stage_id: ''})}};
}

/** Why an item cannot be recorded, or '' (an empty time is fine; a wrong one is not dropped quietly). */
function whyNot(i) {
  if (!i.title) return '題名がありません';
  if (!i.date) return '日付がありません';
  if (!isDay(i.date)) return `日付（${i.date}）が実在しません`;
  if (i.time && !isTime(i.time)) return `時刻（${i.time}）は 00:00〜23:59 で書いてください`;
  return '';
}

/** POST /api/import_works -> {added, skipped, rejected: [{index, title, reason}]} */
async function worksAction(input, ctx) {
  const all = itemsOf(input).map(i => ({
    title: text(i.title, 200), date: text(i.date, 20), venue: text(i.venue, 80),
    time: text(i.time, 10), stage_id: STAGE_ID.test(i.stage_id || '') ? i.stage_id : '',
  }));
  const rejected = [], items = [];
  all.forEach((i, index) => { const reason = whyNot(i); if (reason) rejected.push({index, title: i.title, reason}); else items.push(i); });
  if (!items.length) throw new ValueError(`記録できるものがありません（${rejected.slice(0, 3).map(r => `${r.title || `${r.index + 1} 件目`}：${r.reason}`).join(' / ')}）`);
  // A stage id is kept only if the catalogue has it (never trust the browser's link).
  const ids = [...new Set(items.map(i => i.stage_id).filter(Boolean))];
  const known = new Set();
  if (ids.length) {
    const qs = ids.map(() => '?').join(',');
    const [past, cur] = await ctx.db.batch([
      ctx.db.prepare(`SELECT stage_id FROM past_stage WHERE stage_id IN (${qs})`).bind(...ids),
      ctx.db.prepare(`SELECT stage_id FROM rec_stage WHERE ver=(SELECT v FROM rec_meta WHERE k='current') AND stage_id IN (${qs})`).bind(...ids),
    ]);
    for (const r of [...past.results, ...cur.results]) known.add(String(r.stage_id));
  }
  const rows = items.map(i => ({...i, stage_id: known.has(i.stage_id) ? i.stage_id : '', key: `${titleKey(i.title)}#${i.date}`}));
  const keys = [...new Set(rows.map(r => r.key))];
  const exists = new Set((await ctx.db.prepare(`SELECT work_key FROM works WHERE user_id=? AND work_key IN (${keys.map(() => '?').join(',')})`)
    .bind(ctx.uid, ...keys).all()).results.map(r => r.work_key));
  const fresh = [];
  for (const r of rows) if (!exists.has(r.key)) { exists.add(r.key); fresh.push(r); }
  if (fresh.length) {
    const at = localNow(ctx.now);
    await ctx.db.batch(fresh.map(r => ctx.db.prepare('INSERT OR IGNORE INTO works (user_id, work_key, title, first_date, last_date, times, verdict,'
      + ' chosen, note_impression, note_motive, stage_id, venue, time, updated_at)'
      + " VALUES (?,?,?,?,?,1,NULL,NULL,'','',?,?,?,?)")
      .bind(ctx.uid, r.key, r.title, r.date, r.date, r.stage_id || null, r.venue, r.time, at)));
    const unlinked = fresh.filter(r => !r.stage_id).map(r => r.key);
    if (unlinked.length) await autoLink(ctx, unlinked);
  }
  return {body: {ok: true, added: fresh.length, skipped: rows.length - fresh.length, rejected}};
}

export const importScreens = {
  screens: {},
  actions: {import_match: matchAction, import_works: worksAction},
};

// ---------------------------------------------------------------- calendar fetch
// Google Calendar does not let a page read the iCal address directly (no CORS),
// so the Worker fetches it for the signed-in user and hands the text back
// as is. Only Google's secret/public iCal addresses are accepted (never an
// arbitrary URL), the address and the calendar are not stored, and the size is
// capped.
export const ICS_MAX = 8 * 1024 * 1024;
const GOOGLE_ICS = /^https:\/\/calendar\.google\.com\/calendar\/ical\/[A-Za-z0-9%._@\-]{3,200}\/(?:private-[0-9a-f]{16,64}|public)\/basic\.ics$/;
export function calendarUrl(value) {
  if (typeof value !== 'string') return '';
  const v = value.trim().replace(/^webcal:\/\//i, 'https://');
  return GOOGLE_ICS.test(v) ? v : '';
}
export async function fetchCalendar(value, fetcher = fetch) {
  const url = calendarUrl(value);
  if (!url) return {status: 400, error: 'Google カレンダーの「iCal 形式の非公開アドレス」を貼ってください。'};
  let res;
  try { res = await fetcher(url, {redirect: 'manual', headers: {accept: 'text/calendar'}}); }
  catch { return {status: 502, error: 'カレンダーを読み込めませんでした。'}; }
  if (res.status !== 200 || !res.body) return {status: 502, error: res.status === 404 ? 'このアドレスのカレンダーは見つかりませんでした。アドレスを確かめてください。' : 'カレンダーを読み込めませんでした。'};
  if (Number(res.headers.get('content-length') || 0) > ICS_MAX) return {status: 413, error: 'カレンダーが大きすぎます。読み込めるのは 8MB までです。'};
  let seen = 0;
  const cap = new TransformStream({transform(chunk, c) {
    seen += chunk.byteLength;
    if (seen > ICS_MAX) c.error(new Error('too large'));
    else c.enqueue(chunk);
  }});
  return {status: 200, body: res.body.pipeThrough(cap)};
}
