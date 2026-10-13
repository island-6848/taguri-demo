// 日記帳: the writes made from a record's edit box. Ports of the serve.py
// handlers (on_fix_work, on_merge_work, on_drop_work, on_restore_work,
// on_purge_work, on_hand_credits, on_link_stage, on_visit_note) and the
// app.py / rate_performances.py functions they call, for a public-service
// user: every record is a manual one (no purchases, so no `shows`, no
// corrections table), and serve._enrich (fetching a stage's material) is
// skipped on the public service.
import {strip, slice, field, pyRepr, localNow, dumps, ValueError, WS} from './py.js';
import {loadWorks, similarWorks, titleKey, norm} from './works.js';
import {handCreditCount} from './credits.js';

/** Python truthiness of a value parsed from a JSON body. */
export const truthy = v => !(v === undefined || v === null || v === false || v === 0 || v === ''
  || (Array.isArray(v) && !v.length) || (typeof v === 'object' && !Array.isArray(v) && v !== null && !Object.keys(v).length));
/** str(x) of a value parsed from a JSON body (None for JSON null). */
const pyStrAny = v => typeof v === 'string' ? v : pyRepr(v ?? null);
/** str(b.get(name) or "") */
const req = (b, name, message) => { const v = field(b, name); if (!v) throw new ValueError(message); return v; };
const now = ctx => localNow(ctx.now);
const isDigits = s => /^\p{Nd}+$/u.test(s);

/** rate_performances.read_works for one key: the saved row, whatever its state. */
const savedWork = (ctx, key) => ctx.db.prepare('SELECT * FROM works WHERE user_id=? AND work_key=?').bind(ctx.uid, key).first();

/** rate_performances.save_excluded */
async function saveExcluded(ctx, pairs, excluded) {
  const stmts = pairs.map(([u, p]) => excluded
    ? ctx.db.prepare('INSERT INTO excluded (user_id, uid, program, updated_at) VALUES (?, ?, ?, ?)'
      + ' ON CONFLICT(user_id, uid, program) DO UPDATE SET updated_at=excluded.updated_at').bind(ctx.uid, u, p, now(ctx))
    : ctx.db.prepare('DELETE FROM excluded WHERE user_id = ? AND uid = ? AND program = ?').bind(ctx.uid, u, p));
  if (stmts.length) await ctx.db.batch(stmts);
}

/** rate_performances.read_hand: work_key -> {fields, poster} (a broken row reads as empty). */
async function readHand(ctx) {
  const {results} = await ctx.db.prepare('SELECT work_key, fields, poster FROM hand_credits WHERE user_id=?').bind(ctx.uid).all();
  const out = {};
  for (const r of results) {
    let f;
    try { f = JSON.parse(r.fields || '{}'); } catch { f = {}; }
    out[r.work_key] = {fields: f && typeof f === 'object' && !Array.isArray(f) ? f : {}, poster: r.poster || ''};
  }
  return out;
}

/** rate_performances.save_hand: the side not given is left as it is; an emptied row is removed. */
async function saveHand(ctx, workKey, {fields = null, poster = null} = {}) {
  if (!workKey) throw new ValueError('work_key が要る');
  const t = now(ctx);
  const stmts = [ctx.db.prepare("INSERT INTO hand_credits (user_id, work_key, fields, poster, updated_at)"
    + " VALUES (?, ?, '{}', '', ?) ON CONFLICT(user_id, work_key) DO NOTHING").bind(ctx.uid, workKey, t)];
  if (fields !== null) stmts.push(ctx.db.prepare('UPDATE hand_credits SET fields = ?, updated_at = ? WHERE user_id = ? AND work_key = ?').bind(dumps(fields), t, ctx.uid, workKey));
  if (poster !== null) stmts.push(ctx.db.prepare('UPDATE hand_credits SET poster = ?, updated_at = ? WHERE user_id = ? AND work_key = ?').bind(poster, t, ctx.uid, workKey));
  stmts.push(ctx.db.prepare("DELETE FROM hand_credits WHERE user_id = ? AND work_key = ? AND poster = '' AND fields IN ('{}', '')").bind(ctx.uid, workKey));
  await ctx.db.batch(stmts);
}

// ---------------------------------------------------------------- fix_work
/** corrections._clean_value */
function cleanValue(f, value) {
  const v = strip(String(value ?? '').replace(new RegExp(`[${WS}]+`, 'gu'), ' '));
  if (f === 'date') {
    if (!v) return '';
    if (!/^\p{Nd}{4}-\p{Nd}{2}-\p{Nd}{2}$/u.test(v)) throw new ValueError('上演日は YYYY-MM-DD で入れる');
    return v;
  }
  if (f === 'time') {
    if (!v) return '';
    if (!/^\p{Nd}{2}:\p{Nd}{2}$/u.test(v)) throw new ValueError('開演時刻は HH:MM で入れる');
    return v;
  }
  return slice(v, 0, f === 'title' ? 200 : 80);
}

/** app._fix_manual */
async function fixManual(ctx, workKey, title, shows) {
  const sv = await savedWork(ctx, workKey);
  if (!sv) throw new ValueError('その記録は見つからない');
  const newTitle = title !== null ? strip(title) : (sv.title || '');
  let date = sv.first_date || '', venue = sv.venue || '', time = sv.time || '';
  for (const row of shows) {
    date = cleanValue('date', row.date);
    venue = cleanValue('venue', row.venue);
    time = cleanValue('time', row.time);
  }
  const key = `${titleKey(newTitle)}#${date || 'undated'}`;
  if (key !== workKey && await savedWork(ctx, key)) throw new ValueError('その題名・日付の記録はもう別にある');
  await ctx.db.prepare('UPDATE works SET work_key=?, title=?, first_date=?, last_date=?, venue=?, time=?, updated_at=?'
    + ' WHERE user_id=? AND work_key=?')
    .bind(key, newTitle, date, date || sv.last_date, venue, time, now(ctx), ctx.uid, workKey).run();
  return {ok: true, work_key: key, title: norm(newTitle), moved: key !== workKey, gone: false, n: 1, manual: true};
}

/** serve.on_fix_work + app.fix_work / app.unfix_work (POST /api/fix_work) */
async function fixWorkAction(b, ctx) {
  const workKey = req(b, 'work_key', 'work_key が要る');
  if (truthy(b.clear)) {
    // unfix_work: a manual record has no corrections to take back.
    throw new ValueError('その記録は購入から導けない（手で足した記録は直しを持たない）');
  }
  const title = b.title === undefined || b.title === null ? null : slice(pyStrAny(b.title), 0, 200);
  const shows = (Array.isArray(b.shows) ? b.shows : [])
    .filter(s => s && typeof s === 'object' && !Array.isArray(s))
    .map(s => ({uid: field(s, 'uid'), date: field(s, 'date'), time: slice(field(s, 'time'), 0, 5), venue: slice(field(s, 'venue'), 0, 80)}));
  if (title !== null && !strip(title)) throw new ValueError('題名を空にはできない（抽出結果に戻すなら「戻す」を押す）');
  const out = await fixManual(ctx, workKey, title, shows);
  if (title !== null && !out.gone) out.similar = await similarWorks(ctx, out.title || title, out.work_key || workKey);
  return {body: out};
}

// ---------------------------------------------------------------- merge_work
/** app.merge_works */
async function mergeWorks(ctx, workKey, otherKey) {
  const ws = new Map((await loadWorks(ctx)).map(w => [w.work_key, w]));
  const a = ws.get(workKey), b = ws.get(otherKey);
  if (!a || !b) throw new ValueError('その記録は見つからない');
  if (workKey === otherKey) throw new ValueError('同じ記録どうしはまとめられない');
  // Manual records have no mails (shows), so the earlier one is kept.
  const [keep, drop] = (a.first_date || '9999') <= (b.first_date || '9999') ? [a, b] : [b, a];
  await ctx.db.prepare('INSERT INTO merges (user_id, work_key, into_key, updated_at) VALUES (?,?,?,?)'
    + ' ON CONFLICT(user_id, work_key) DO UPDATE SET into_key=excluded.into_key, updated_at=excluded.updated_at')
    .bind(ctx.uid, drop.work_key, keep.work_key, now(ctx)).run();
  const kv = (await savedWork(ctx, keep.work_key)) || {}, dv = (await savedWork(ctx, drop.work_key)) || {};
  const moved = [];
  if (!(kv.verdict || '') && (dv.verdict || '')) moved.push('評価');
  if (!strip(kv.note_impression || '') && strip(dv.note_impression || '')) moved.push('感想');
  if (moved.length) {
    await ctx.db.prepare('INSERT INTO works (user_id, work_key, title, first_date, last_date, times,'
      + ' verdict, chosen, note_impression, note_motive, updated_at)'
      + " VALUES (?,?,?,?,?,?,?,?,?,'',?)"
      + ' ON CONFLICT(user_id, work_key) DO UPDATE SET verdict=COALESCE(works.verdict,'
      + " excluded.verdict), note_impression=CASE WHEN trim(works.note_impression)=''"
      + ' THEN excluded.note_impression ELSE works.note_impression END,'
      + ' updated_at=excluded.updated_at')
      .bind(ctx.uid, keep.work_key, keep.title, keep.first_date || '', keep.last_date || '', keep.times || 1,
        dv.verdict ?? null, kv.chosen ?? null, dv.note_impression || '', now(ctx)).run();
  }
  const hand = await readHand(ctx);
  const kh = hand[keep.work_key] || {}, dh = hand[drop.work_key] || {};
  const takeFields = !handCreditCount(kh.fields || {}) && Boolean(handCreditCount(dh.fields || {}));
  const takePoster = !(kh.poster || '') && Boolean(dh.poster || '');
  if (takeFields) moved.push('手で入れた出演者');
  if (takePoster) moved.push('手で入れたポスター');
  if (takeFields || takePoster) {
    await saveHand(ctx, keep.work_key, {fields: takeFields ? (dh.fields || {}) : null, poster: takePoster ? (dh.poster || '') : null});
  }
  return {ok: true, kept: keep.work_key, kept_title: keep.title, dropped: drop.work_key, dropped_title: drop.title, moved};
}

/** serve.on_merge_work (POST /api/merge_work) */
async function mergeWorkAction(b, ctx) {
  const workKey = req(b, 'work_key', 'work_key が要る');
  if (truthy(b.unmerge)) {
    const r = await ctx.db.prepare('DELETE FROM merges WHERE user_id=? AND into_key=?').bind(ctx.uid, workKey).run();
    return {body: {ok: true, n: r.meta?.changes ?? r.changes ?? 0}};
  }
  return {body: await mergeWorks(ctx, workKey, field(b, 'other'))};
}

// ---------------------------------------------------------------- drop / restore / purge
/** serve.on_drop_work + app.drop_work (POST /api/drop_work) */
async function dropWorkAction(b, ctx) {
  const workKey = req(b, 'work_key', 'work_key が要る');
  const w = (await loadWorks(ctx)).find(x => x.work_key === workKey);
  if (!w) throw new ValueError('その記録は見つからない');
  await saveExcluded(ctx, [[`work:${workKey}`, w.title]], true);
  return {body: {ok: true, work_key: workKey, title: w.title, n: 1}};
}

/** app._dropped_state for a public user (no purchases: no record owns a mail). */
async function droppedState(ctx) {
  const {results} = await ctx.db.prepare('SELECT uid, program FROM excluded WHERE user_id = ? ORDER BY uid, program').bind(ctx.uid).all();
  const ex = results.map(r => [r.uid, r.program]);
  const marks = new Map(ex.filter(([u]) => u.startsWith('work:')).map(([u, p]) => [u.slice(5), p]));
  const purged = new Set(ex.filter(([u]) => u.startsWith('purged:')).map(([u]) => u.slice(7)));
  const purgedLegacy = new Set(ex.filter(([u]) => u.startsWith('purged-legacy:')).map(([, p]) => p));
  return {ex, marks, purged, purgedLegacy};
}

/** serve.on_restore_work + app.restore_work (POST /api/restore_work) */
async function restoreWorkAction(b, ctx) {
  const key = req(b, 'key', 'key が要る');
  const {ex, marks} = await droppedState(ctx);
  const pairs = marks.has(key) ? [[`work:${key}`, marks.get(key)]]
    : ex.filter(([u, p]) => !u.startsWith('work:') && p === key);
  if (!pairs.length) throw new ValueError('外した記録に見つからない');
  await saveExcluded(ctx, pairs, false);
  return {body: {ok: true, key, n: pairs.length}};
}

/** serve.on_purge_work + app.purge_work (POST /api/purge_work) */
async function purgeWorkAction(b, ctx) {
  const key = req(b, 'key', 'key が要る');
  const {ex, marks, purged, purgedLegacy} = await droppedState(ctx);
  let title;
  if (marks.has(key) && !purged.has(key)) {
    title = marks.get(key);
    await saveExcluded(ctx, [[`work:${key}`, title]], false);
    await saveExcluded(ctx, [[`purged:${key}`, title]], true);
  } else if (!purgedLegacy.has(key) && ex.some(([u, p]) => p === key && !u.startsWith('work:') && !u.startsWith('purged:') && !u.startsWith('purged-legacy:'))) {
    title = key;
    await saveExcluded(ctx, [[`purged-legacy:${key}`, key]], true);
  } else {
    throw new ValueError('取り消した記録に見つからない');
  }
  return {body: {ok: true, key, title}};
}

// ---------------------------------------------------------------- hand_credits
/** app.HAND_FIELDS keys */
const HAND_KEYS = ['出演', '演出', '脚本', 'スタッフ'];

/** serve.on_hand_credits + app.save_hand_credits (POST /api/hand_credits) */
async function handCreditsAction(b, ctx) {
  const workKey = req(b, 'work_key', 'work_key が要る');
  const fields = b.fields;
  if (!fields || typeof fields !== 'object' || Array.isArray(fields)) throw new ValueError('欄が要る');
  const keep = {};
  for (const k of HAND_KEYS) {
    const v = strip(field(fields, k));
    if (v) keep[k] = slice(v, 0, 4000);
  }
  await saveHand(ctx, workKey, {fields: keep});
  const n = handCreditCount(keep);
  return {body: {ok: true, n, fields: keep, said: n ? `${n} 名を名簿に入れました` : '手で入れた出演者を消しました'}};
}

// ---------------------------------------------------------------- link_stage
/** The stage's title in the public catalogue (stage_label.title), '' if it is not there. */
async function stageTitle(ctx, sid) {
  const r = await ctx.db.prepare("SELECT title FROM stage_label WHERE ver=(SELECT v FROM rec_meta WHERE k='stage_label') AND stage_id=?").bind(sid).first();
  return r?.title || '';
}

/** serve.on_link_stage + app.link_stage (POST /api/link_stage) */
async function linkStageAction(b, ctx) {
  const workKey = field(b, 'work_key');
  const stageId = slice(strip(field(b, 'stage_id')), 0, 16);
  if (!workKey) throw new ValueError('work_key が要る');
  if (stageId && !/^\p{Nd}{1,12}$/u.test(stageId)) throw new ValueError('公演の id が数字ではない');
  if (stageId && !isDigits(stageId)) throw new ValueError('公演の id は数字である');
  const w = (await loadWorks(ctx)).find(x => x.work_key === workKey);
  if (!w) throw new ValueError('その記録は見つからない');
  let title = '';
  if (stageId) {
    title = await stageTitle(ctx, stageId);
    if (!title) throw new ValueError('たぐりの公演一覧にある公演から選んでください。無い公演は「探す」から、次の更新で探すよう頼めます');
  }
  await ctx.db.prepare('INSERT INTO works (user_id, work_key, title, first_date, last_date, times,'
    + " verdict, chosen, note_impression, note_motive, stage_id, updated_at)"
    + " VALUES (?,?,?,?,?,?,NULL,NULL,'','',?,?)"
    + ' ON CONFLICT(user_id, work_key) DO UPDATE SET stage_id=excluded.stage_id, updated_at=excluded.updated_at')
    .bind(ctx.uid, workKey, w.title, w.first_date || '', w.last_date || '', w.times || 1, stageId || null, now(ctx)).run();
  return {body: {ok: true, work_key: workKey, stage_id: stageId, title}};
}

// ---------------------------------------------------------------- visit_note
/** serve.on_visit_note + rate_performances.save_visit_note (POST /api/visit_note) */
async function visitNoteAction(b, ctx) {
  const uid = field(b, 'uid');
  const note = slice(field(b, 'note'), 0, 4000);
  if (!uid) throw new ValueError('uid が要る');
  await ctx.db.prepare('INSERT INTO visit_note (user_id, uid, note, updated_at) VALUES (?, ?, ?, ?)'
    + ' ON CONFLICT(user_id, uid) DO UPDATE SET note=excluded.note, updated_at=excluded.updated_at')
    .bind(ctx.uid, uid, note, now(ctx)).run();
  return {body: {uid, len: Array.from(note).length}};
}

export const diaryScreens = {
  screens: {},
  actions: {fix_work: fixWorkAction, merge_work: mergeWorkAction, drop_work: dropWorkAction,
    restore_work: restoreWorkAction, purge_work: purgeWorkAction, hand_credits: handCreditsAction,
    link_stage: linkStageAction, visit_note: visitNoteAction},
};
