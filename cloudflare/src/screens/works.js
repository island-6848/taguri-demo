// A user's works (観た作品), read from D1 the way tools/taguri/app.py reads
// them from ratings.db. Public-service users never import mail, so every row is
// a manual one (rate_performances.load_purchases returns [] for them): the
// purchase / attendance / splits / credits.jsonl paths of app._works are empty
// and are not ported.
import {WS, strip, seqRatio, pyRound, sortBy, localNow, cmp} from './py.js';

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
// 画面を読むときに消すのは 1 回にこの件数まで（issue #194）。前は 1 件ごとに batch を流していたので、まとめて取り消した人が
// 後で開くと 1 回の表示で N 回の batch になった。残りは隠したまま、次に読んだときに消す。消すのは 1 回の batch・5 文で、
// 書き込みは消える行と、その行ごとの rec_rev の進め（migrations/0035 のトリガー）。50 件で多くて 500 行ほど（D1 の 1 日 10 万行の 0.5%）。
export const EXPIRE_MAX = 50;
export const deleteWork = (ctx, key) => deleteWorks(ctx, [key]);
/** 記録をまとめて消す。鍵は JSON の 1 つの値で渡す（json_each。D1 の 1 文の引数は 100 個まで） */
export async function deleteWorks(ctx, keys) {
  if (!keys.length) return;
  const ks = JSON.stringify(keys);
  const marks = JSON.stringify(keys.flatMap(k => [`work:${k}`, `purged:${k}`]));
  const today = ctx.today || new Date((ctx.now ?? Date.now()) + 9 * 3600e3).toISOString().slice(0, 10);
  const q = (sql, ...v) => ctx.db.prepare(sql).bind(ctx.uid, ...v);
  await ctx.db.batch([
    // 行く日が過ぎた券から作った記録（lists.promoteTickets）を消したときは、その回の券も消す（行かなかった回は作り直さない）。
    // 記録を消す前に、その記録の公演・日・時刻で引く
    q(`DELETE FROM ticket WHERE user_id=?1 AND EXISTS(SELECT 1 FROM works w WHERE w.user_id=?1
      AND w.work_key IN (SELECT value FROM json_each(?2)) AND w.stage_id IS NOT NULL AND w.stage_id<>''
      AND ticket.stage_id=CAST(w.stage_id AS TEXT) AND COALESCE(w.first_date,'')<>'' AND w.first_date<=?3 AND ticket.date=w.first_date
      AND (COALESCE(w.time,'')='' OR ticket.time='' OR ticket.time=w.time))`, ks, today),
    q('DELETE FROM works WHERE user_id=?1 AND work_key IN (SELECT value FROM json_each(?2))', ks),
    q('DELETE FROM hand_credits WHERE user_id=?1 AND work_key IN (SELECT value FROM json_each(?2))', ks),
    q('DELETE FROM work_piece WHERE user_id=?1 AND work_key IN (SELECT value FROM json_each(?2))', ks),
    q('DELETE FROM merges WHERE user_id=?1 AND (work_key IN (SELECT value FROM json_each(?2)) OR into_key IN (SELECT value FROM json_each(?2)))', ks),
    q('DELETE FROM excluded WHERE user_id=?1 AND uid IN (SELECT value FROM json_each(?2))', marks),
  ]);
}
/** この時刻より前に取り消した記録は消す（消しきれていなくても、もう出さない） */
export const dropCutoff = ctx => localNow((ctx.now ?? Date.now()) - DROP_KEEP_DAYS * 864e5);
/** 消す記録の鍵: 30 日たった取り消し（work:<key>）と、前の版で「完全に取り消す」を押したもの（purged:<key>） */
export function expiredKeys(ctx, rows) {
  const cutoff = dropCutoff(ctx);
  const keys = new Set();
  for (const r of rows) {
    if (r.uid.startsWith('purged:')) keys.add(r.uid.slice(7));
    else if (r.uid.startsWith('work:') && String(r.updated_at) < cutoff) keys.add(r.uid.slice(5));
  }
  return keys;
}
export async function expireDropped(ctx) {
  if (ctx.dropExpired) return;
  ctx.dropExpired = true;
  const {results} = await ctx.db.prepare("SELECT uid, updated_at FROM excluded WHERE user_id=? AND (uid LIKE 'work:%' OR uid LIKE 'purged:%')")
    .bind(ctx.uid).all();
  await deleteWorks(ctx, [...expiredKeys(ctx, results)].slice(0, EXPIRE_MAX));
}

/**
 * 1 回の観劇で観た複数の作品を、作品ごとに分けた中身（work_piece、dec-split-pieces）。記録の鍵 -> 並び順の作品。
 * 分けていない記録には無い（記録は 1 公演 1 行のまま）
 */
async function readPieces(ctx) {
  // 表がまだ無い D1（migration 0042 の前に新しいコードが動いたとき）でも、記録の画面は止めずに「分けていない」として読む
  let results = [];
  try {
    ({results} = await ctx.db.prepare('SELECT work_key, idx, title, verdict, aspects, note, cast_in, rated_at FROM work_piece WHERE user_id=? ORDER BY work_key, idx')
      .bind(ctx.uid).all());
  } catch { results = []; }
  const out = new Map();
  for (const r of results) { if (!out.has(r.work_key)) out.set(r.work_key, []); out.get(r.work_key).push(r); }
  return out;
}
/** その作品に出ていた出演者の Set（work_piece.cast_in）。空・読めないときは null（公演の出演者の全員） */
export function pieceCast(p) {
  try { const v = JSON.parse(p?.cast_in || '[]'); return Array.isArray(v) && v.length ? new Set(v.filter(x => typeof x === 'string')) : null; } catch { return null; }
}
export async function loadWorks(ctx) {
  await expireDropped(ctx);
  const [saved, excluded, merges, hand, pieces] = await Promise.all([
    readWorks(ctx),
    ctx.db.prepare('SELECT uid FROM excluded WHERE user_id=?').bind(ctx.uid).all(),
    ctx.db.prepare('SELECT work_key, into_key FROM merges WHERE user_id=?').bind(ctx.uid).all(),
    readHand(ctx), readPieces(ctx)]);
  // Records taken back ("work:<key>") and records merged into another one drop out.
  // 消す前の記録（purged:<key>、上限で消しきれなかった分）も、ここで外れる。
  const dropped = new Set(excluded.results.filter(r => r.uid.startsWith('work:') || r.uid.startsWith('purged:')).map(r => r.uid.slice(r.uid.indexOf(':') + 1)));
  const mergedInto = new Map(merges.results.map(r => [r.work_key, r.into_key]));
  const out = [], into = new Map();
  for (const sv of saved) {
    const k = sv.work_key;
    if (dropped.has(k)) continue;
    if (mergedInto.has(k)) {
      const dst = mergedInto.get(k);
      if (!into.has(dst)) into.set(dst, []);
      // まとめた回も、観た日・劇場・開演・回数・公演を残す（日記帳で回ごとに出し、回数・劇場を数えるため。起案者の問い 2026-10-21
      // 「ツアー公演を複数回追加するとき、またまとめた公演を見るとき周辺のUXが悪い」── 前は題名だけを残し、7 回観ても 1 回に見えた）
      into.get(dst).push({work_key: k, title: sv.title || '', first_date: sv.first_date || '', last_date: sv.last_date || '',
        times: sv.times || 1, venue: sv.venue || '', time: sv.time || '', stage_id: sv.stage_id || ''});
      continue;
    }
    // Links made by screens/autolink.js carry stage_auto=1 (shown as 自動で結び付けました).
    out.push({work_key: k, title: sv.title || '', bucket: 'manual',
      first_date: sv.first_date || '', last_date: sv.last_date || '',
      times: sv.times || 1, verdict: sv.verdict || '', note_impression: sv.note_impression || '',
      aspects: sv.aspects || '', cast_off: sv.cast_off || '',
      venue: sv.venue || '', time: sv.time || '', stage_id: sv.stage_id || '',
      auto_linked: !!sv.stage_auto && !!sv.stage_id, has_credits: false, unseen: false, skipped: 0,
      suspect: false, merged: [], hand: hand[k] || {}, shows: [], pieces: pieces.get(k) || []});
  }
  for (const w of out) {
    if (into.has(w.work_key)) w.merged = [...w.merged, ...into.get(w.work_key)];
    w.visits = visitsOf(w);
    w.seen_times = w.visits.reduce((n, v) => n + v.times, 0);
    // 並びは、まとめた回も入れていちばん後に観た日（ツアーの最後の回を 8 月に観たなら、7 月の所に埋もれない）
    w.seen_last = w.visits.reduce((d, v) => (v.last_date > d ? v.last_date : d), w.last_date || '');
  }
  // out.sort(key=lambda w: w["last_date"] or "0000", reverse=True) — stable.
  return sortBy(out, w => w.seen_last || w.last_date || '0000', true);
}

/**
 * 記録の観た回 [{work_key, date, last_date, time, venue, stage_id, times, kept}]。残した記録（kept）と、まとめた記録（merged）の
 * 1 件ずつを、観た日・開演の順に。loadWorks を通った記録は w.visits に入っている
 */
export function visitsOf(w) {
  if (Array.isArray(w.visits)) return w.visits;
  const one = (x, kept) => ({work_key: x.work_key, date: x.first_date || '', last_date: x.last_date || x.first_date || '',
    time: x.time || '', venue: x.venue || '', stage_id: x.stage_id || '', times: Number(x.times) || 1, kept});
  return [one(w, true), ...(w.merged || []).map(m => one(m, false))]
    .sort((a, b) => cmp(a.date || '9999', b.date || '9999') || cmp(a.time, b.time));
}
/** 観た回数: まとめた回も入れ、記録ごとの回数（times）を足す。アカウント・日記帳・眺める・評価で同じ数にする */
export const seenTimes = w => w.seen_times ?? visitsOf(w).reduce((n, v) => n + v.times, 0);

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
