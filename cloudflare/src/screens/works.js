// A user's works (観た作品), read from D1 the way tools/taguri/app.py reads
// them from ratings.db. Public-service users never import mail, so every row is
// a manual one (rate_performances.load_purchases returns [] for them): the
// purchase / attendance / splits / credits.jsonl paths of app._works are empty
// and are not ported.
import {WS, strip, seqRatio, pyRound, sortBy, localNow} from './py.js';

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
// 取り消した記録は 30 日で本当に消す（起案者の指示 2026-10-14「取り消した記録は30日以内に復元されなかったら
// 自動的に削除して」）。それまでは excluded の印（work:<key>）で隠しているだけで、記録は works に残っている。
// 前の版で「完全に取り消す」（purged:<key>）を押したものも、ここで消す。記録を読むたびに、この人の印だけを見る（数行）。
export const DROP_KEEP_DAYS = 30;
export async function deleteWork(ctx, key) {
  // 行く日が過ぎた券から作った記録（lists.promoteTickets）を消したときは、その回の券も消す（行かなかった回は作り直さない）
  const w = await ctx.db.prepare('SELECT stage_id,first_date,time FROM works WHERE user_id=? AND work_key=?').bind(ctx.uid, key).first();
  const today = ctx.today || new Date((ctx.now ?? Date.now()) + 9 * 3600e3).toISOString().slice(0, 10);
  const pastTicket = w?.stage_id && w.first_date && w.first_date <= today
    ? [ctx.db.prepare("DELETE FROM ticket WHERE user_id=? AND stage_id=? AND date=? AND (?='' OR time='' OR time=?)").bind(ctx.uid, String(w.stage_id), w.first_date, w.time || '', w.time || '')]
    : [];
  await ctx.db.batch([
    ...pastTicket,
    ctx.db.prepare('DELETE FROM works WHERE user_id=? AND work_key=?').bind(ctx.uid, key),
    ctx.db.prepare('DELETE FROM hand_credits WHERE user_id=? AND work_key=?').bind(ctx.uid, key),
    ctx.db.prepare('DELETE FROM merges WHERE user_id=? AND (work_key=? OR into_key=?)').bind(ctx.uid, key, key),
    ctx.db.prepare("DELETE FROM excluded WHERE user_id=? AND uid IN (?, ?)").bind(ctx.uid, `work:${key}`, `purged:${key}`),
  ]);
}
export async function expireDropped(ctx) {
  if (ctx.dropExpired) return;
  ctx.dropExpired = true;
  const cutoff = localNow((ctx.now ?? Date.now()) - DROP_KEEP_DAYS * 864e5);
  const {results} = await ctx.db.prepare("SELECT uid, updated_at FROM excluded WHERE user_id=? AND (uid LIKE 'work:%' OR uid LIKE 'purged:%')")
    .bind(ctx.uid).all();
  const keys = new Set();
  for (const r of results) {
    if (r.uid.startsWith('purged:')) keys.add(r.uid.slice(7));
    else if (String(r.updated_at) < cutoff) keys.add(r.uid.slice(5));
  }
  for (const k of keys) await deleteWork(ctx, k);
}

export async function loadWorks(ctx) {
  await expireDropped(ctx);
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
    // Links made by screens/autolink.js carry stage_auto=1 (shown as 自動で結び付けました).
    out.push({work_key: k, title: sv.title || '', bucket: 'manual',
      first_date: sv.first_date || '', last_date: sv.last_date || '',
      times: sv.times || 1, verdict: sv.verdict || '', note_impression: sv.note_impression || '',
      aspects: sv.aspects || '', cast_off: sv.cast_off || '',
      venue: sv.venue || '', time: sv.time || '', stage_id: sv.stage_id || '',
      auto_linked: !!sv.stage_auto && !!sv.stage_id, has_credits: false, unseen: false, skipped: 0,
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
