// Linking a user's record to the stage they saw, automatically.
//
// 起案者の指示（2026-10-13）「いちいち結びつけなくても、過去の公演の情報紐づいてほしい」
// (docs/knowledge: q-auto-link-past). The matching follows link_works.find —
// the viewing date inside the stage's run and the same title — but is stricter:
// the title key (rate_performances.title_key) must be equal, and exactly one
// stage may match. A wrong link is worse than none: it puts strangers on the
// user's roster.
//
// Stages to match against: past_stage (CoRich pages from 2019 on, read daily
// by tools/review/fetch_past_stages.py) and the current index (rec_stage:
// upcoming stages and those ended within 180 days).
//
// A record is never linked again once the user removed its link (works.stage_off,
// set by link_stage with an empty id). Links made here carry works.stage_auto=1
// so the edit box says 「自動で結び付けました。違っていたら直してください」.
import {titleKey} from './works.js';

const PER_QUERY = 90;          // D1 binds at most 100 parameters
const MAX_WORKS = 200;         // records examined per call (screens call this on every view)

/** Stages per title key: tkey -> [{stage_id, start, end}] from past_stage and the current index. */
async function stagesByKey(db, keys) {
  const out = new Map();
  const add = r => {
    if (!out.has(r.tkey)) out.set(r.tkey, []);
    out.get(r.tkey).push({stage_id: String(r.stage_id), start: r.start || '', end: r.end || ''});
  };
  for (let i = 0; i < keys.length; i += PER_QUERY) {
    const part = keys.slice(i, i + PER_QUERY), qs = part.map(() => '?').join(',');
    const [past, cur] = await db.batch([
      db.prepare(`SELECT stage_id, tkey, start, end FROM past_stage WHERE tkey IN (${qs})`).bind(...part),
      db.prepare(`SELECT stage_id, tkey, start, end FROM rec_stage WHERE ver=(SELECT v FROM rec_meta WHERE k='current') AND tkey IN (${qs})`).bind(...part),
    ]);
    for (const r of past.results) add(r);
    for (const r of cur.results) add(r);
  }
  return out;
}

/** The one stage running on `date` among `stages`, or '' (none, or more than one). */
export function pickStage(stages, date) {
  if (!date) return '';
  const hit = new Set(stages
    .filter(s => s.start && s.start <= date && date <= (s.end || s.start))
    .map(s => s.stage_id));
  return hit.size === 1 ? [...hit][0] : '';
}

/**
 * Link the user's unlinked records that match exactly one stage. `keys`
 * limits it to those work_keys (after add_work / fix_work). Returns
 * {work_key: stage_id} for the links made.
 */
export async function autoLink(ctx, keys = null) {
  const db = ctx.db;
  let sql = "SELECT work_key, title, first_date FROM works WHERE user_id=? AND (stage_id IS NULL OR stage_id='')"
    + " AND stage_off=0 AND first_date IS NOT NULL AND first_date<>''";
  const args = [ctx.uid];
  if (keys) {
    if (!keys.length) return {};
    sql += ` AND work_key IN (${keys.map(() => '?').join(',')})`;
    args.push(...keys);
  }
  let rows;
  try {
    rows = (await db.prepare(sql + ` LIMIT ${MAX_WORKS}`).bind(...args).all()).results;
  } catch {
    return {};      // a database without migration 0012: nothing to match against yet
  }
  if (!rows.length) return {};
  const tk = new Map(rows.map(r => [r.work_key, titleKey(r.title)]));
  const want = [...new Set([...tk.values()].filter(k => Array.from(k).length >= 2))];
  if (!want.length) return {};
  let byKey;
  try {
    byKey = await stagesByKey(db, want);
  } catch {
    return {};
  }
  const made = {};
  for (const r of rows) {
    const sid = pickStage(byKey.get(tk.get(r.work_key)) || [], r.first_date);
    if (sid) made[r.work_key] = sid;
  }
  const entries = Object.entries(made);
  if (!entries.length) return {};
  // Only fill an empty link, and never one the user removed (checked again at write time).
  await db.batch(entries.map(([k, sid]) => db.prepare(
    "UPDATE works SET stage_id=?, stage_auto=1 WHERE user_id=? AND work_key=? AND (stage_id IS NULL OR stage_id='') AND stage_off=0")
    .bind(sid, ctx.uid, k)));
  return made;
}

/** past_stage rows for the given ids: stage_id -> {title, venue, start, end, people}. */
export async function pastStages(db, ids) {
  const out = {};
  const want = [...new Set(ids.filter(Boolean).map(String))];
  for (let i = 0; i < want.length; i += PER_QUERY) {
    const part = want.slice(i, i + PER_QUERY);
    let results;
    try {
      ({results} = await db.prepare(`SELECT stage_id, title, venue, start, end, people FROM past_stage WHERE stage_id IN (${part.map(() => '?').join(',')})`)
        .bind(...part).all());
    } catch {
      return out;
    }
    for (const r of results) {
      let people;
      try { people = JSON.parse(r.people || '[]'); } catch { people = []; }
      out[r.stage_id] = {title: r.title, venue: r.venue || '', start: r.start || '', end: r.end || '', people};
    }
  }
  return out;
}
