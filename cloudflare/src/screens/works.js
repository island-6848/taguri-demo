// A user's works (観た作品), read from D1 the way tools/taguri/app.py reads
// them from ratings.db. Public-service users never import mail, so every row is
// a manual one (rate_performances.load_purchases returns [] for them): the
// purchase / attendance / splits / credits.jsonl paths of app._works are empty
// and are not ported.
import {WS, strip, seqRatio, pyRound, sortBy} from './py.js';

// rate_performances.title_key: drop a leading crown (〈…〉【…】) and symbols/spaces.
const CROWN = new RegExp(`^[〈<（(【\\[][^\\n]{0,12}?[〉>）)】\\]][${WS}]*`, 'u');
const DROP = new RegExp(`[『』「」【】〈〉\\[\\]（）()・･,，\\.。${WS}\\-−–—~〜/／:：!！?？'"“”’]`, 'gu');
/** rate_performances.norm */
export const norm = s => strip(String(s || '').normalize('NFKC'));
/** rate_performances.title_key */
export const titleKey = title => norm(title).replace(CROWN, '').replace(DROP, '').toLowerCase();

/** rate_performances.read_works: work_key -> saved row. The SELECT walks the
 * (user_id, work_key) primary key in both databases, so rows come in work_key
 * (code point) order; ORDER BY makes that explicit. */
async function readWorks(ctx) {
  const {results} = await ctx.db.prepare('SELECT * FROM works WHERE user_id=? ORDER BY work_key').bind(ctx.uid).all();
  return results;
}

/** rate_performances.read_hand: work_key -> {fields, poster}. */
async function readHand(ctx) {
  const {results} = await ctx.db.prepare('SELECT work_key, fields, poster FROM hand_credits WHERE user_id=? ORDER BY work_key').bind(ctx.uid).all();
  const out = {};
  for (const r of results) {
    let f;
    try { f = JSON.parse(r.fields || '{}'); } catch { f = {}; }
    out[r.work_key] = {fields: f && typeof f === 'object' && !Array.isArray(f) ? f : {}, poster: r.poster || ''};
  }
  return out;
}

/** app._works for a public-service user (manual rows only). */
export async function loadWorks(ctx) {
  const [saved, excluded, merges, hand] = await Promise.all([
    readWorks(ctx),
    ctx.db.prepare('SELECT uid FROM excluded WHERE user_id=?').bind(ctx.uid).all(),
    ctx.db.prepare('SELECT work_key, into_key FROM merges WHERE user_id=?').bind(ctx.uid).all(),
    readHand(ctx)]);
  // Records taken back ("work:<key>") and records merged into another one drop out.
  const dropped = new Set(excluded.results.filter(r => r.uid.startsWith('work:')).map(r => r.uid.slice(5)));
  const mergedInto = new Map(merges.results.map(r => [r.work_key, r.into_key]));
  const out = [], into = new Map();
  for (const sv of saved) {
    const k = sv.work_key;
    if (dropped.has(k)) continue;
    if (mergedInto.has(k)) {
      const dst = mergedInto.get(k);
      if (!into.has(dst)) into.set(dst, []);
      into.get(dst).push({work_key: k, title: sv.title || ''});
      continue;
    }
    // data/credits/linked.jsonl (auto links) is the owner's batch output; a
    // public user's rows are never auto-linked, so auto_linked stays false.
    out.push({work_key: k, title: sv.title || '', bucket: 'manual',
      first_date: sv.first_date || '', last_date: sv.last_date || '',
      times: sv.times || 1, verdict: sv.verdict || '', note_impression: sv.note_impression || '',
      venue: sv.venue || '', time: sv.time || '', stage_id: sv.stage_id || '',
      auto_linked: false, has_credits: false, unseen: false, skipped: 0,
      suspect: false, merged: [], hand: hand[k] || {}, shows: []});
  }
  for (const w of out) if (into.has(w.work_key)) w.merged = [...w.merged, ...into.get(w.work_key)];
  // out.sort(key=lambda w: w["last_date"] or "0000", reverse=True) — stable.
  return sortBy(out, w => w.last_date || '0000', true);
}

/** app.similar_works: records whose title is close to `title` (never merged automatically). */
export async function similarWorks(ctx, title, excludeKey = '', limit = 5) {
  const k = Array.from(titleKey(title || ''));
  if (k.length < 2) return [];
  const ks = k.join('');
  const out = [];
  for (const w of await loadWorks(ctx)) {
    if (w.work_key === excludeKey) continue;
    const wk = titleKey(w.title);
    if (!wk) continue;
    let score;
    if (wk === ks) score = 1.0;
    else if ((ks.includes(wk) || wk.includes(ks)) && Math.min(Array.from(wk).length, k.length) >= 4) score = 0.9;
    else {
      score = seqRatio(ks, wk);
      if (score < 0.72) continue;
    }
    out.push({work_key: w.work_key, title: w.title, first_date: w.first_date || '',
      last_date: w.last_date || '', times: w.times || 1, verdict: w.verdict || '',
      mails: w.shows.length, score: pyRound(score, 3)});
  }
  return sortBy(out, r => -r.score).slice(0, limit);
}
