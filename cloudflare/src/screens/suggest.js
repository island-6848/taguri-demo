// GET /api/suggest (and /api/suggest_web, which the public Python service answers
// the same way: neither searches CoRich on the spot, #92 — the screens say so and
// offer 「次の更新で探してもらう」 (search_request) for stages not in D1): stages and the user's own records whose title matches what is
// being typed, for linking a record to a stage. Answered by the Worker once
// production no longer goes to Render (NATIVE_UI=all): Render's answer mixed in
// the demo's records as "your" records.
//
// Same response shape as app.suggest ({q, rows:[{kind,key,title,date,venue,note,
// times,stage_id,wk,mine,poster}]}) plus the stage's run (start, end: the 観た日 picker opens there), but not a byte-for-byte port: the stages
// come from D1 (current stages through rec_gram, past stages by title-key
// prefix on its index) instead of the files on the Python server.
import {gradeText} from './grade.js';
import {titleKey, d1Search, searchIndex, titlePrefixes, prefixWhere} from '../stage-search.js';
import {loadWorks} from './works.js';
import {scheduleFilter} from './schedule-filter.js';

const LIMIT = 8;
const PAST_LIMIT = 20;
const DETAIL_SCAN_LIMIT = 200; // Manual search only; never scan the whole archive for a venue/date.

const ymd = s => /^(\d{4})[-/](\d{1,2})[-/](\d{1,2})/.exec(s || '');
/** render_recommend.run_range: "10/2〜10/3", with years when not this year or across years. */
export function runRange(start, end, today) {
  const a = ymd(start), b = ymd(end) || a, ty = (today || '').slice(0, 4);
  if (!a) return '';
  const md = m => `${Number(m[2])}/${Number(m[3])}`;
  const years = a[1] !== b[1] || a[1] !== ty;
  const one = m => (years ? `${m[1]}/` : '') + md(m);
  return a[0] === b[0] ? one(a) : `${one(a)}〜${one(b)}`;
}
const iso = m => m ? `${m[1]}-${m[2].padStart(2, '0')}-${m[3].padStart(2, '0')}` : '';
const groupKey = (k, group, sid) => group ? `${k}|${group.normalize('NFKC').trim()}` : `${k}|@${sid}`;

export async function suggest(params, ctx) {
  const q = (params.get('q') || '').slice(0, 120);
  const k = titleKey(q);
  if (Array.from(k).length < 2) return {q, rows: []};
  const advanced = params.get('advanced') === '1';
  const venue = advanced ? (params.get('venue') || '').trim().slice(0, 80) : '';
  const group = advanced ? (params.get('group') || '').trim().slice(0, 80) : '';
  let schedule;
  try { schedule = scheduleFilter(advanced ? params : new URLSearchParams()); }
  catch (error) { return {q, rows: [], error: error.message}; }
  const fits = (v, g, start, end) => (!venue || (v || '').includes(venue))
    && (!group || (g || '').includes(group)) && schedule.matches(start, end);
  const db = ctx.db;
  const works = (await loadWorks(ctx)).filter(w => !w.unseen);
  const mine = {};
  for (const w of works) if (w.stage_id) mine[w.stage_id] = (mine[w.stage_id] || 0) + (w.times || 1);
  const rank = tk => tk === k ? 0 : tk.startsWith(k) ? 1 : tk.includes(k) ? 2 : (k.includes(tk) && Array.from(tk).length >= 4) ? 3 : -1;
  const rows = [];
  for (const w of works) {
    if (advanced) continue; // Select the production, rather than an existing attendance.
    const s = rank(titleKey(w.title));
    if (s < 0) continue;
    rows.push({_s: [s, 0], kind: 'record', key: w.work_key, title: w.title, date: w.first_date || '', venue: '',
      note: w.verdict ? '評価 ' + gradeText(w.verdict) : '評価はまだです', times: w.times || 1, stage_id: w.stage_id || '',
      wk: groupKey(titleKey(w.title), '', w.stage_id || w.work_key)});
  }
  const ver = (await db.prepare("SELECT v FROM rec_meta WHERE k='current'").first())?.v;
  const seen = new Set();
  if (ver) {
    const search = d1Search(db, ver);
    const ids = await search.stages(await searchIndex(search.entriesFor, q, schedule.from || ctx.today,
      advanced ? DETAIL_SCAN_LIMIT : undefined));
    for (const st of ids) {
      if (!fits(st.theater, st.group, st.start, st.end)) continue;
      seen.add(st.stage_id);
      const one = runRange(st.start, st.end, ctx.today);
      rows.push({_s: [rank(titleKey(st.title)) < 0 ? 2 : rank(titleKey(st.title)), 1], kind: 'stage', key: st.stage_id, title: st.title,
        date: one && !one.includes('〜') ? iso(ymd(st.start)) : '', venue: st.theater,
        note: `${st.group}／${one}（${st.pref}）`, times: 1, stage_id: st.stage_id, start: iso(ymd(st.start)), end: iso(ymd(st.end || st.start)),
        wk: groupKey(titleKey(st.title), st.group, st.stage_id)});
    }
  }
  // Past stages: titles starting with what was typed (the tkey index; a scan for
  // "contains" would read every row on each keystroke). 「舞台」「ミュージカル」など題名の頭に付く語の後ろも
  // 先頭一致で引く（stage-search.titlePrefixes、起案者の指摘 2026-10-19）
  const keys = titlePrefixes(k), pw = prefixWhere(keys);
  const filters = [], args = [...pw.args];
  if (venue) { filters.push("instr(COALESCE(venue,''),?)>0"); args.push(venue); }
  if (group) { filters.push("instr(COALESCE(grp,''),?)>0"); args.push(group); }
  if (schedule.from) { filters.push("start<=? AND COALESCE(NULLIF(end,''),start)>=?"); args.push(schedule.to, schedule.from); }
  const pastQuery = `SELECT stage_id,title,tkey,start,end,venue,grp,pref FROM past_stage WHERE ${pw.sql}`;
  const {results: past} = await db.prepare((advanced
    ? `SELECT * FROM (${pastQuery} ORDER BY tkey LIMIT ${DETAIL_SCAN_LIMIT})` + (filters.length ? ' WHERE ' + filters.join(' AND ') : '')
    : pastQuery) + ' ORDER BY tkey LIMIT ?')
    .bind(...args, advanced ? DETAIL_SCAN_LIMIT : PAST_LIMIT).all();
  for (const p of past.filter(p => fits(p.venue, p.grp, p.start, p.end)).slice(0, PAST_LIMIT)) {
    if (seen.has(p.stage_id)) continue;
    const one = runRange(p.start, p.end, ctx.today);
    rows.push({_s: [keys.includes(p.tkey) ? 0 : 1, 1], kind: 'stage', key: p.stage_id, title: p.title,
      date: one && !one.includes('〜') ? iso(ymd(p.start)) : '', venue: p.venue,
      note: `${p.grp}／${one}（${p.pref}）`, times: 1, stage_id: p.stage_id, start: iso(ymd(p.start)), end: iso(ymd(p.end || p.start)),
      wk: groupKey(p.tkey, p.grp, p.stage_id)});
  }
  rows.sort((a, b) => (a._s[0] - b._s[0]) || (a._s[1] - b._s[1]));
  // Count the limit in works, not rows: a touring work has a row per venue.
  const kept = [], groups = new Set();
  for (const r of rows) {
    const g = r.kind + '\u0000' + r.wk;
    if (!groups.has(g) && groups.size >= LIMIT) continue;
    groups.add(g);
    kept.push(r);
    if (kept.length >= LIMIT * 8) break;
  }
  const sids = [...new Set(kept.map(r => r.stage_id).filter(Boolean))];
  const posters = {};
  for (let i = 0; i < sids.length; i += 90) {
    const part = sids.slice(i, i + 90);
    const {results} = await db.prepare(`SELECT stage_id,file FROM poster WHERE stage_id IN (${part.map(() => '?').join(',')})`).bind(...part).all();
    for (const r of results) posters[r.stage_id] = r.file;
  }
  return {q, rows: kept.map(({_s, ...r}) => ({...r, mine: mine[r.stage_id] || 0, poster: posters[r.stage_id] || ''}))};
}

