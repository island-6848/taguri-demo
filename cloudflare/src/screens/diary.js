// 日記帳: the writes made from a record's edit box. Ports of the serve.py
// handlers (on_fix_work, on_merge_work, on_drop_work, on_restore_work,
// on_purge_work, on_hand_credits, on_link_stage, on_visit_note) and the
// app.py / rate_performances.py functions they call, for a public-service
// user: every record is a manual one (no purchases, so no `shows`, no
// corrections table), and serve._enrich (fetching a stage's material) is
// skipped on the public service.
import {scaleOf} from './grade.js';
import {autoLink, pastStages} from './autolink.js';
import {E, strip, slice, field, pyRepr, localNow, dumps, ValueError, WS, quote, qsFirst, sortBy, cmp, isdigit} from './py.js';
import {loadWorks, similarWorks, titleKey, norm, deleteWork} from './works.js';
import {handCreditCount, parseCredits} from './credits.js';
import {recRow, anchor, stageLabels} from './row.js';
import {rowInfos} from './rowinfo.js';
import {indexTabs, paginate, page as pageOf, SHEET_TOP, posterHtml, posterFiles} from './rate.js';

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
async function saveHand(ctx, workKey, opts = {}) {
  await ctx.db.batch(handStatements(ctx, workKey, opts));
}
/** saveHand の文（ほかの書き込みと 1 つの batch にまとめるとき用、#187） */
function handStatements(ctx, workKey, {fields = null, poster = null} = {}) {
  if (!workKey) throw new ValueError('work_key が要る');
  const t = now(ctx);
  const stmts = [ctx.db.prepare("INSERT INTO hand_credits (user_id, work_key, fields, poster, updated_at)"
    + " VALUES (?, ?, '{}', '', ?) ON CONFLICT(user_id, work_key) DO NOTHING").bind(ctx.uid, workKey, t)];
  if (fields !== null) stmts.push(ctx.db.prepare('UPDATE hand_credits SET fields = ?, updated_at = ? WHERE user_id = ? AND work_key = ?').bind(dumps(fields), t, ctx.uid, workKey));
  if (poster !== null) stmts.push(ctx.db.prepare('UPDATE hand_credits SET poster = ?, updated_at = ? WHERE user_id = ? AND work_key = ?').bind(poster, t, ctx.uid, workKey));
  stmts.push(ctx.db.prepare("DELETE FROM hand_credits WHERE user_id = ? AND work_key = ? AND poster = '' AND fields IN ('{}', '')").bind(ctx.uid, workKey));
  return stmts;
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

/**
 * 鍵（work_key）で記録に結び付いている行を、古い鍵から新しい鍵へ移す文（issue #186）。works の書き換えと同じ batch で流す。
 * 手で入れた出演者（hand_credits）・まとめた印（merges の両側）・取り消しの印（excluded の work:<key>・purged:<key>）。
 * どれも利用者と古い鍵で絞る。前の版で取り残された行が新しい鍵に残っていれば、古い鍵の行があるときだけ先に消す（主キーがぶつかるため）。
 */
function moveKey(ctx, from, to) {
  const q = sql => ctx.db.prepare(sql).bind(ctx.uid, from, to);
  const stmts = [];
  for (const t of ['hand_credits', 'merges']) {
    stmts.push(q(`DELETE FROM ${t} WHERE user_id=?1 AND work_key=?3 AND EXISTS(SELECT 1 FROM ${t} WHERE user_id=?1 AND work_key=?2)`),
      q(`UPDATE ${t} SET work_key=?3 WHERE user_id=?1 AND work_key=?2`));
  }
  stmts.push(q('UPDATE merges SET into_key=?3 WHERE user_id=?1 AND into_key=?2'),
    // 取り残された印で、自分自身にまとめた形になったら外す（その記録が一覧から消えるため）
    q('DELETE FROM merges WHERE user_id=?1 AND work_key=?3 AND into_key=?3'));
  for (const p of ['work:', 'purged:']) {
    stmts.push(ctx.db.prepare('DELETE FROM excluded WHERE user_id=?1 AND uid=?3 AND EXISTS(SELECT 1 FROM excluded WHERE user_id=?1 AND uid=?2)').bind(ctx.uid, p + from, p + to),
      ctx.db.prepare('UPDATE excluded SET uid=?3 WHERE user_id=?1 AND uid=?2').bind(ctx.uid, p + from, p + to));
  }
  return stmts;
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
  await ctx.db.batch([ctx.db.prepare('UPDATE works SET work_key=?, title=?, first_date=?, last_date=?, venue=?, time=?, updated_at=?'
    + ' WHERE user_id=? AND work_key=?')
    .bind(key, newTitle, date, date || sv.last_date, venue, time, now(ctx), ctx.uid, workKey),
  ...(key !== workKey ? moveKey(ctx, workKey, key) : [])]);
  await autoLink(ctx, [key]);
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
  // 先に読むだけ読み、まとめた印・評価と感想の移動・手で入れた出演者の移動は 1 つの batch で書く（#187）。
  // 前は印を先に書いていたので、後の書き込みが失敗すると印だけが残り、評価の無いまま片方が隠れた。
  const kv = (await savedWork(ctx, keep.work_key)) || {}, dv = (await savedWork(ctx, drop.work_key)) || {};
  const hand = await readHand(ctx);
  const stmts = [ctx.db.prepare('INSERT INTO merges (user_id, work_key, into_key, updated_at) VALUES (?,?,?,?)'
    + ' ON CONFLICT(user_id, work_key) DO UPDATE SET into_key=excluded.into_key, updated_at=excluded.updated_at')
    .bind(ctx.uid, drop.work_key, keep.work_key, now(ctx))];
  const moved = [];
  if (!(kv.verdict || '') && (dv.verdict || '')) moved.push('評価');
  if (!strip(kv.note_impression || '') && strip(dv.note_impression || '')) moved.push('感想');
  if (moved.length) {
    stmts.push(ctx.db.prepare('INSERT INTO works (user_id, work_key, title, first_date, last_date, times,'
      + ' verdict, chosen, note_impression, note_motive, updated_at, rated_at)'
      + " VALUES (?,?,?,?,?,?,?,?,?,'',?,?)"
      + ' ON CONFLICT(user_id, work_key) DO UPDATE SET verdict=COALESCE(works.verdict,'
      + " excluded.verdict), note_impression=CASE WHEN trim(works.note_impression)=''"
      + ' THEN excluded.note_impression ELSE works.note_impression END,'
      // 移した評価は、評価した時刻（rated_at、#112）も一緒に移す
      + ' rated_at=CASE WHEN works.verdict IS NULL THEN excluded.rated_at ELSE works.rated_at END,'
      + ' updated_at=excluded.updated_at')
      .bind(ctx.uid, keep.work_key, keep.title, keep.first_date || '', keep.last_date || '', keep.times || 1,
        dv.verdict ?? null, kv.chosen ?? null, dv.note_impression || '', now(ctx), dv.verdict ? (dv.rated_at || dv.updated_at || null) : null));
  }
  const kh = hand[keep.work_key] || {}, dh = hand[drop.work_key] || {};
  const takeFields = !handCreditCount(kh.fields || {}) && Boolean(handCreditCount(dh.fields || {}));
  const takePoster = !(kh.poster || '') && Boolean(dh.poster || '');
  if (takeFields) moved.push('手で入れた出演者');
  if (takePoster) moved.push('手で入れたポスター');
  if (takeFields || takePoster) {
    stmts.push(...handStatements(ctx, keep.work_key, {fields: takeFields ? (dh.fields || {}) : null, poster: takePoster ? (dh.poster || '') : null}));
  }
  await ctx.db.batch(stmts);
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
    // 完全に取り消す: the record itself goes now, not after DROP_KEEP_DAYS (works.expireDropped).
    title = marks.get(key);
    await deleteWork(ctx, key);
  } else if (!purgedLegacy.has(key) && ex.some(([u, p]) => p === key && !u.startsWith('work:') && !u.startsWith('purged:') && !u.startsWith('purged-legacy:'))) {
    title = key;
    await saveExcluded(ctx, [[`purged-legacy:${key}`, key]], true);
  } else {
    throw new ValueError('取り消した記録に見つからない');
  }
  return {body: {ok: true, key, title}};
}

// ---------------------------------------------------------------- cast_seen
// 観た回の出演者（起案者の指示 2026-10-15「Wキャストの出演者を選べるようにして」）。
// {work_key} だけなら、つながった公演の出演者と、いま外している人を返す。
// {work_key, off: [名前]} なら、観た回に出ていなかった人として保存する（推薦はこの記録の材料から外す）。
export const CAST_OFF_MAX = 200;
export const castOffOf = w => {
  try { const v = JSON.parse(w?.cast_off || '[]'); return Array.isArray(v) ? v.filter(x => typeof x === 'string') : []; } catch { return []; }
};
async function castSeenAction(b, ctx) {
  const key = req(b, 'work_key', 'work_key が要る');
  const w = await ctx.db.prepare('SELECT stage_id, cast_off FROM works WHERE user_id=? AND work_key=?').bind(ctx.uid, key).first();
  if (!w) throw new ValueError('その記録は見つからない');
  if (!w.stage_id) throw new ValueError('観た公演がまだつながっていません');
  const cast = await castOfStage(ctx, w.stage_id);
  if (b.off === undefined) return {body: {ok: true, work_key: key, cast, off: castOffOf(w).filter(n => cast.includes(n))}};
  if (!Array.isArray(b.off) || b.off.length > CAST_OFF_MAX || b.off.some(n => typeof n !== 'string' || !cast.includes(n)))
    throw new ValueError('出演者の名前が公演のものと合いません');
  if (b.off.length && b.off.length >= cast.length) throw new ValueError('観た回の出演者を 1 人以上残してください');
  const off = cast.filter(n => b.off.includes(n));
  await ctx.db.batch([
    ctx.db.prepare('UPDATE works SET cast_off=? WHERE user_id=? AND work_key=?').bind(off.length ? JSON.stringify(off) : '', ctx.uid, key),
    // 推薦の控えを捨てる（updated_at は評価の時刻として裏の答え合わせが使うので動かさない）。
    ctx.db.prepare('DELETE FROM rec_cache WHERE user_id=?').bind(ctx.uid)]);
  return {body: {ok: true, work_key: key, off}};
}
/** 公演の出演者（索引 rec_people、無ければ過去の公演 past_stage）の名前、出てくる順。 */
async function castOfStage(ctx, sid) {
  const ver = (await ctx.db.prepare("SELECT v FROM rec_meta WHERE k='current'").first())?.v;
  let row = ver ? await ctx.db.prepare('SELECT people FROM rec_people WHERE ver=? AND stage_id=?').bind(ver, sid).first() : null;
  if (!row) { try { row = await ctx.db.prepare('SELECT people FROM past_stage WHERE stage_id=?').bind(sid).first(); } catch { row = null; } }
  let people = [];
  try { people = JSON.parse(row?.people || '[]'); } catch { people = []; }
  return [...new Set(people.filter(p => Array.isArray(p) && p[0] === '出演' && typeof p[1] === 'string').map(p => p[1]))];
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
  if (r?.title) return r.title;
  // A past stage (past_stage, 2019 onwards) can be linked by hand too.
  return (await pastStages(ctx.db, [sid]))[sid]?.title || '';
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
  // Linked by hand: no longer an automatic link. Unlinked: never link this record automatically again.
  await ctx.db.prepare("UPDATE works SET stage_auto=0, stage_off=?, cast_off='' WHERE user_id=? AND work_key=?")
    .bind(stageId ? 0 : 1, ctx.uid, workKey).run();
  return {body: {ok: true, work_key: workKey, stage_id: stageId, title}};
}

// ---------------------------------------------------------------- unseen
/**
 * serve.on_unseen + app.set_unseen (POST /api/unseen): 「行かなかった」. It is
 * written per visit of a purchase; a public-service user's records are all
 * added by hand (no visits), so set_unseen always names the other way out.
 */
async function unseenAction(b, ctx) {
  const workKey = field(b, 'work_key');
  if (!workKey) throw new ValueError('work_key が要る');
  if (typeof b.unseen !== 'boolean') throw new ValueError('unseen は真偽で渡す');
  const w = (await loadWorks(ctx)).find(x => x.work_key === workKey);
  if (!w) throw new ValueError('その記録は見つからない');
  if (!(w.shows || []).length) {
    throw new ValueError('この記録は購入から来ていないので、「この記録を取り消す」から外してほしい');
  }
  throw new ValueError('購入から来た記録は、この版にはない');
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

// ---------------------------------------------------------------- 日記帳 (screen)
/**
 * measure_nets.load_rated(include_unrated=True) for a public user: work_key ->
 * sorted unique [role, person] from the linked stage's credits (rec_people,
 * built from measure_nets._fields_by_stage by build_recommend_index.py) plus
 * the hand-entered ones.
 */
export async function peopleByKey(ctx, ws) {
  const sids = [...new Set(ws.map(w => w.stage_id).filter(Boolean))];
  const stage = {};
  for (let i = 0; i < sids.length; i += 90) {
    const part = sids.slice(i, i + 90);
    const {results} = await ctx.db.prepare("SELECT stage_id, people FROM rec_people WHERE ver=(SELECT v FROM rec_meta WHERE k='current')"
      + ` AND stage_id IN (${part.map(() => '?').join(',')})`).bind(...part).all();
    // Rows whose role starts with "#" (形式・原作・翻訳・会場, person-ordinal-v3) describe
    // the stage, not its people: load_rated's parse_credits never returns them.
    for (const r of results) stage[r.stage_id] = JSON.parse(r.people).filter(([role]) => !String(role).startsWith('#'));
  }
  // Stages linked from past_stage (older than the current index) bring their own credits.
  const past = await pastStages(ctx.db, sids.filter(s => !stage[s]));
  for (const [sid, p] of Object.entries(past)) stage[sid] = p.people.filter(([role]) => !String(role).startsWith('#'));
  const out = {};
  for (const w of ws) {
    const people = [...(stage[w.stage_id] || []), ...parseCredits((w.hand || {}).fields || {})];
    const seen = new Map(people.map(p => [p[0] + '\u0000' + p[1], p]));
    out[w.work_key] = [...seen.values()].sort((a, b) => cmp(a[0], b[0]) || cmp(a[1], b[1]));
  }
  return out;
}

/** app._records_lede */
export function recordsLede(d) {
  const skip = !d.nSkip ? '' : `<br>「行かなかった」と答えた ${d.nSkip} 件は、件数と図から外しています。`
    + '「日記帳」には出さずに「設定」の「行かなかった公演」にまとめてあります。「やはり観た」で戻せます。';
  return `<p class="lede">観た記録は <b>${d.seen.length} 作品</b>です`
    + `（評価が付いているのは ${d.nRated} 件、感想が書いてあるのは `
    + `${d.nNotes} 件）。この画面の数字は、すべて手元のデータだけで作っています。`
    + `${skip}</p>`;
}

/** app._records_empty_note */
export const RECORDS_EMPTY = '<p class="pnow">観た公演の記録がまだ無いので、図は出せません。'
  + '「<a href="/register?t=__TAGURI_TOKEN__">観劇記録を追加</a>」から'
  + '購入確認メールを取り込むか、観た公演を手で足すと、'
  + '<b>本数・評価の分かれ方・行った場所・時期</b>がここに出ます。</p>';

/** app._check_line */
const checkLine = n => !n
  ? '<b>いまのところ、読み取りを間違えたらしい記録はありません。</b>見つかったものは、この一覧の先頭に出します。'
  : `購入確認メールの読み取りに失敗した跡（括弧が閉じていないなど）がある記録が ${n} 件あります。`
    + `<b>この ${n} 件を先に出しています。</b>`
    + '直した内容は次の取り込みと公演ページの検索にも使われます。';

/**
 * app._works_body (GET /api/screen/works?y=&p=&w=&g=). Posters are not on the
 * Worker (rate.posterHtml), and the rated-side synopses (themes.jsonl) are the
 * owner's batch output keyed by the owner's records, so none are shown.
 */
async function worksScreen(params, ctx) {
  await autoLink(ctx);
  const ws = await loadWorks(ctx);
  const seen = ws.filter(w => !w.unseen);
  const d = {seen, nSkip: ws.length - seen.length, nRated: seen.filter(w => w.verdict).length,
    nNotes: seen.filter(w => strip(w.note_impression || '')).length};
  const people = await peopleByKey(ctx, ws);
  let year = qsFirst(params, 'y'), group = qsFirst(params, 'g', 'work'), page = pageOf(params);
  const want = qsFirst(params, 'w');
  const check = ws.filter(w => w.suspect);
  let rest = ws.filter(w => !w.suspect && !w.unseen);
  // app._flatten_visits: a manual record has no mails to open, so only the order changes.
  const restVisit = sortBy(rest, w => w.first_date || '0000', true);
  const groups = [['work', '作品でまとめる', rest.length], ['visit', 'すべて表示', restVisit.length]];
  group = ['work', 'visit'].includes(group) ? group : 'work';
  if (group === 'visit') rest = restVisit;
  const years = new Map();
  for (const w of rest) {
    const y = slice(w.first_date || '', 0, 4);
    const k = isdigit(y) ? y : 'none';
    if (!years.has(k)) years.set(k, []);
    years.get(k).push(w);
  }
  const keys = [...years.keys()].filter(k => k !== 'none').sort(cmp).reverse();
  if (years.has('none')) keys.push('none');
  const piles = new Map(keys.map(k => [k, years.get(k)]));
  if (check.length) piles.set('check', check);
  const order = [...(check.length ? ['check'] : []), ...keys];
  const title = '日記帳';
  if (!order.length) {
    return {title, body_html: `<h1>日記帳</h1>\n${recordsLede(d)}\n${RECORDS_EMPTY}`};
  }
  const label = {none: '上演日が分からない', check: '先に確かめてほしい'};
  const tabs = order.map(k => [k, label[k] ?? `${k} 年`, piles.get(k).length]);
  let sel = piles.has(year) ? year : (keys.length ? keys[0] : order[0]);
  if (want) {
    found: for (const k of order) {
      for (const [n, w] of piles.get(k).entries()) {
        if (anchor(w.work_key) === want) { sel = k; page = Math.floor(n / SHEET_TOP) + 1; break found; }
      }
    }
  }
  const hit = piles.get(sel);
  const url = (k, pg = 1, g = '') => '/records/works?t=__TAGURI_TOKEN__'
    + (k ? `&amp;y=${quote(k)}` : '') + (pg > 1 ? `&amp;p=${pg}` : '') + (g && g !== 'work' ? `&amp;g=${g}` : '');
  const [show, now, foot] = paginate(hit, page, SHEET_TOP, pg => url(sel, pg, group), '件');
  const lead = sel === 'check' ? '読み取りに失敗した跡がある記録です。年をまたいで散らばるので、1 枚にまとめてあります。'
    : sel === 'none' ? '上演日が分からない記録です。日付が無いと年で分けられないので、1 枚にまとめてあります。'
      : `${sel} 年に観た記録です。`;
  const nCast = ws.filter(w => (people[w.work_key] || []).some(([r]) => r === '出演')).length;
  const gnote = group === 'work'
    ? '同じ作品は 1 行にまとめています。複数回観ていれば、日付は最初に観た日を出し、「N 回観た」と添えます。'
    : '観た回ごとに 1 行で出しています。「すべて表示」はまとめずに 1 回ずつ出すという意味です。'
      + '同じ作品を複数回観ていれば、行った日の数だけ並びます。'
      + '評価と感想は回ごとには記録していないので、どの行にも同じものが出ます。'
      + '<b>「この回のメモ」だけは行ごとに別々に書けます</b>。このメモは推薦には使いません。';
  const labels = await stageLabels(ctx, show.map(w => w.stage_id));
  const files = await posterFiles(ctx, show);
  const scale = await scaleOf(ctx);
  const infos = await rowInfos(ctx, show, people);
  const rows = show.map(w => recRow({...w, people: people[w.work_key] || [], synopsis: '', info: infos[w.work_key]},
    {poster: posterHtml(w, files), editable: true, label: labels[w.stage_id] || '', scale, fullDate: true})).join('');
  return {title, body_html: `<h1>日記帳</h1>
${recordsLede(d)}
<p class="lede">1 件ごとに、日付・評価・感想が出ます。<b>感想は各行の「感想」の鉛筆から書けます</b>。書いた感想は欄から離れたときに保存されます。
<b>題名・上演日・劇場は、各行の「公演詳細を直す」から直せます。</b>ポスターを出せたのは 0 件、
あらすじは 0 件、出演者は ${nCast} 件です。${gnote}
${checkLine(check.length)}</p>
${indexTabs(groups, group, g => url(piles.has(sel) ? sel : '', 1, g), '作品でまとめる・すべて表示を切り替える')}
${indexTabs(tabs, sel, k => url(k, 1, group), '年で切り替える')}
<div class="idxsheet">
<p class="mnow">${lead}${now}上のインデックスで、ほかの年に切り替えられます。</p>
${rows}</div>
${foot}`};
}

export const diaryScreens = {
  screens: {works: worksScreen},
  actions: {fix_work: fixWorkAction, merge_work: mergeWorkAction, drop_work: dropWorkAction,
    restore_work: restoreWorkAction, purge_work: purgeWorkAction, hand_credits: handCreditsAction,
    link_stage: linkStageAction, visit_note: visitNoteAction, unseen: unseenAction, cast_seen: castSeenAction},
};
