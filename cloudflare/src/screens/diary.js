// 日記帳: the writes made from a record's edit box. Ports of the serve.py
// handlers (on_fix_work, on_merge_work, on_drop_work, on_restore_work,
// on_purge_work, on_hand_credits, on_link_stage, on_visit_note) and the
// app.py / rate_performances.py functions they call, for a public-service
// user: every record is a manual one (no purchases, so no `shows`, no
// corrections table), and serve._enrich (fetching a stage's material) is
// skipped on the public service.
import {scaleOf, ALL_GRADES, gradeText} from './grade.js';
import {autoLink, pastStages} from './autolink.js';
import {E, strip, slice, field, pyRepr, localNow, dumps, ValueError, WS, quote, qsFirst, sortBy, cmp, isdigit} from './py.js';
import {loadWorks, similarWorks, titleKey, norm, deleteWork, pieceCast, visitsOf} from './works.js';
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
 * 手で入れた出演者（hand_credits）・作品ごとに分けた中身（work_piece）・まとめた印（merges の両側）・取り消しの印（excluded の work:<key>・purged:<key>）。
 * どれも利用者と古い鍵で絞る。前の版で取り残された行が新しい鍵に残っていれば、古い鍵の行があるときだけ先に消す（主キーがぶつかるため）。
 */
function moveKey(ctx, from, to) {
  const q = sql => ctx.db.prepare(sql).bind(ctx.uid, from, to);
  const stmts = [];
  for (const t of ['hand_credits', 'work_piece', 'merges']) {
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

/**
 * 同じ作品の記録を自動でまとめる（起案者の指示 2026-10-19「観劇記録の中でも回は違っても同じ作品なら同じ作品のツリーとして統合する
 * 作業を自動でやって（今ユーザーの手動）」）。手でまとめる（mergeWorks）のと同じ印（merges）を書く。
 * - 同じ作品: 題名の鍵（works.titleKey）が同じで、団体が同じか片方に無い・劇場が同じ・同じ公演に結び付いている、のどれか
 *   （同じ題名の別の上演（別の団体の『ハムレット』）はまとめない。おすすめの束ね方 recommend.sameStage と同じ考え）
 * - 残すのはいちばん早い日の記録（mergeWorks と同じ）
 * - 評価が違う記録・感想を書いた記録が 2 つ以上ある組はまとめない（まとめると片方の評価・感想が隠れるため。手でまとめれば選べる）。
 *   評価が片方だけなら、まとめて残す記録に移す（mergeWorks と同じ）
 * - 本人が「まとめを外す」をした記録（excluded の nomerge:<鍵>）はまとめ直さない
 * 書くのは新しくまとめる組の分だけ。まとめる組が無ければ、読み 2 回（記録・外した印）だけで終わる
 */
export async function autoMerge(ctx, ws = null) {
  ws = (ws || await loadWorks(ctx)).filter(w => !w.unseen && w.work_key);
  const byTitle = new Map();
  for (const w of ws) {
    const k = titleKey(w.title || '');
    if (Array.from(k).length < 2) continue;
    if (!byTitle.has(k)) byTitle.set(k, []);
    byTitle.get(k).push(w);
  }
  const groups = [...byTitle.values()].filter(g => g.length > 1);
  if (!groups.length) return [];
  const {results: off} = await ctx.db.prepare("SELECT uid FROM excluded WHERE user_id=? AND uid LIKE 'nomerge:%'").bind(ctx.uid).all();
  const nomerge = new Set(off.map(r => r.uid.slice('nomerge:'.length)));
  const sids = [...new Set(groups.flat().map(w => String(w.stage_id || '')).filter(Boolean))];
  const grp = new Map();
  for (let i = 0; i < sids.length; i += 90) {
    const part = sids.slice(i, i + 90), qs = part.map(() => '?').join(',');
    const [cur, past] = await Promise.all([
      ctx.db.prepare(`SELECT stage_id, grp, tour FROM rec_stage WHERE ver=(SELECT v FROM rec_meta WHERE k='current') AND stage_id IN (${qs})`).bind(...part).all().catch(() => ({results: []})),
      ctx.db.prepare(`SELECT stage_id, grp, '' AS tour FROM past_stage WHERE stage_id IN (${qs})`).bind(...part).all().catch(() => ({results: []}))]);
    for (const r of [...past.results, ...cur.results]) grp.set(String(r.stage_id), {g: String(r.grp || '').normalize('NFKC').replace(/[\s　]+/gu, ''), tour: r.tour || ''});
  }
  const loose = v => String(v || '').normalize('NFKC').replace(/[\s　]+/gu, '');
  const same = (a, b) => {
    const x = grp.get(String(a.stage_id || '')) || {}, y = grp.get(String(b.stage_id || '')) || {};
    if (a.stage_id && a.stage_id === b.stage_id) return true;
    if (x.tour && x.tour === y.tour) return true;
    if (!x.g || !y.g || x.g === y.g) return true;
    return Boolean(loose(a.venue)) && loose(a.venue) === loose(b.venue);
  };
  // 評価は作品に 1 つ（まとめた回は同じ評価を共有する）。評価が違う記録どうし・感想を書いた記録どうしは、片方が隠れるのでまとめない
  const clash = list => new Set(list.map(w => w.verdict || '').filter(Boolean)).size > 1
    || list.filter(w => strip(w.note_impression || '')).length > 1;
  const done = [];
  for (const g of groups) {
    // 早い日から順に、先に置いた束のどれかと同じ作品なら、その束に入れる
    const sorted = [...g].sort((a, b) => cmp(a.first_date || '9999', b.first_date || '9999'));
    const piles = [];
    for (const w of sorted) {
      const pile = piles.find(p => p.some(x => same(x, w)));
      if (pile) pile.push(w); else piles.push([w]);
    }
    for (const pile of piles) {
      const drops = pile.slice(1).filter(w => !nomerge.has(w.work_key));
      if (!drops.length || clash([pile[0], ...drops])) continue;
      for (const d of drops) done.push(await mergeWorks(ctx, pile[0].work_key, d.work_key));
    }
  }
  return done;
}

/** serve.on_merge_work (POST /api/merge_work) */
async function mergeWorkAction(b, ctx) {
  const workKey = req(b, 'work_key', 'work_key が要る');
  if (truthy(b.unmerge)) {
    // 外した記録は、自動でまとめ直さない（autoMerge の nomerge:<鍵>）。one を渡すと、その 1 回だけを分ける
    // （起案者の問い 2026-10-21。前は全部か無しかで、分けた回は評価が無くなり、未評価に何件も並んだ）
    const one = field(b, 'one');
    const {results: all} = await ctx.db.prepare('SELECT work_key FROM merges WHERE user_id=? AND into_key=?').bind(ctx.uid, workKey).all();
    const drops = one ? all.filter(d => d.work_key === one) : all;
    if (one && !drops.length) throw new ValueError('その回はこの記録にまとまっていない');
    // 評価が無い回には、まとめていた記録の評価（と評価した時刻）を写す。感想は写さない（同じ文が 2 つになるため）
    const kv = (await savedWork(ctx, workKey)) || {};
    const stmts = [];
    for (const d of drops) {
      stmts.push(ctx.db.prepare('DELETE FROM merges WHERE user_id=? AND work_key=?').bind(ctx.uid, d.work_key));
      stmts.push(ctx.db.prepare("INSERT INTO excluded (user_id, uid, program, updated_at) VALUES (?,?,'auto_merge',?) ON CONFLICT DO NOTHING")
        .bind(ctx.uid, 'nomerge:' + d.work_key, now(ctx)));
      if (kv.verdict) {
        stmts.push(ctx.db.prepare("UPDATE works SET verdict=?, rated_at=?, updated_at=? WHERE user_id=? AND work_key=? AND (verdict IS NULL OR verdict='')")
          .bind(kv.verdict, kv.rated_at || kv.updated_at || null, now(ctx), ctx.uid, d.work_key));
      }
    }
    if (stmts.length) await ctx.db.batch(stmts);
    return {body: {ok: true, n: drops.length}};
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
// ---------------------------------------------------------------- pieces
// 1 回の観劇で観た複数の作品を、作品ごとに分ける（起案者の指示 2026-10-19「1 公演を 1 件として表示しつつ、評価や推薦、
// 感想…は作品数分分けられる？ただしユーザーが分けたいとしたときの任意」、dec-split-pieces）。記録は 1 件のまま、
// 作品ごとに作品名・評価・感想・その作品に出ていた出演者を持つ。推薦は作品ごとの評価を使う（recommend.personValues）。
// {work_key} だけなら、いまの中身と、つながった公演の出演者、評価の選択肢を返す。
// {work_key, pieces: [{title, verdict, note, cast}]} なら、まるごと置き換える。[] は分けるのをやめる（記録は残る）。
export const PIECES_MAX = 20, PIECE_TITLE_MAX = 80, PIECE_NOTE_MAX = 4000;
/** 評価の付け方ごとの選択肢（上から） */
const SCALE_GRADES = {marks2: ['2/2', '1/2'], marks3: ['3/3', '2/3', '1/3'], marks4: ['◎', '○', '△', '×'],
  stars5: ['5/5', '4/5', '3/5', '2/5', '1/5'], stars11: Array.from({length: 10}, (_, i) => `${11 - i}/11`)};
async function piecesAction(b, ctx) {
  const key = req(b, 'work_key', 'work_key が要る');
  const w = await ctx.db.prepare('SELECT stage_id FROM works WHERE user_id=? AND work_key=?').bind(ctx.uid, key).first();
  if (!w) throw new ValueError('その記録は見つからない');
  const cast = w.stage_id ? await castOfStage(ctx, w.stage_id) : [];
  const {results: saved} = await ctx.db.prepare('SELECT idx, title, verdict, aspects, note, cast_in, rated_at FROM work_piece WHERE user_id=? AND work_key=? ORDER BY idx')
    .bind(ctx.uid, key).all();
  if (b.pieces === undefined) {
    const grades = (SCALE_GRADES[await scaleOf(ctx)] || SCALE_GRADES.marks4).map(v => [v, gradeText(v)]);
    return {body: {ok: true, work_key: key, cast, grades, max: PIECES_MAX,
      pieces: saved.map(p => ({title: p.title, verdict: p.verdict || '', note: p.note || '', cast: [...(pieceCast(p) || [])].filter(n => cast.includes(n))}))}};
  }
  if (!Array.isArray(b.pieces) || b.pieces.length === 1 || b.pieces.length > PIECES_MAX)
    throw new ValueError(`作品は 2 つから ${PIECES_MAX} までです（分けるのをやめるときは空にします）`);
  const at = now(ctx), seen = new Set(), rows = [];
  for (const [i, p] of b.pieces.entries()) {
    if (!p || typeof p !== 'object') throw new ValueError('作品の中身を確かめてください');
    const title = slice(strip(String(p.title ?? '').replace(new RegExp(`[${WS}]+`, 'gu'), ' ')), 0, PIECE_TITLE_MAX);
    if (!title) throw new ValueError(`${i + 1} つめの作品名を入れてください`);
    if (seen.has(title)) throw new ValueError(`同じ作品名が 2 つあります: ${title}`);
    seen.add(title);
    const verdict = p.verdict ? String(p.verdict) : null;
    if (verdict !== null && !ALL_GRADES.includes(verdict)) throw new ValueError('評価の値が合いません');
    const note = typeof p.note === 'string' ? p.note : '';
    if (Array.from(note).length > PIECE_NOTE_MAX) throw new ValueError(`感想は 1 作品 ${PIECE_NOTE_MAX} 字までです`);
    const names = p.cast === undefined || p.cast === null ? [] : p.cast;
    if (!Array.isArray(names) || names.some(n => typeof n !== 'string' || !cast.includes(n)))
      throw new ValueError('出演者の名前が公演のものと合いません');
    // 全員を選んだときは '' と同じ（公演の出演者が後で増えても全員のまま）
    const picked = cast.filter(n => names.includes(n));
    const castIn = picked.length && picked.length < cast.length ? JSON.stringify(picked) : '';
    // 評価した時刻（rated_at、#112）は、同じ作品名の評価が変わったときだけ進める
    const prev = saved.find(x => x.title === title);
    const ratedAt = !verdict ? null : prev && prev.verdict === verdict && prev.rated_at ? prev.rated_at : at;
    rows.push([i, title, verdict, prev?.aspects || '', note, castIn, ratedAt]);
  }
  await ctx.db.batch([
    ctx.db.prepare('DELETE FROM work_piece WHERE user_id=? AND work_key=?').bind(ctx.uid, key),
    ...rows.map(r => ctx.db.prepare('INSERT INTO work_piece (user_id, work_key, idx, title, verdict, aspects, note, cast_in, rated_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)')
      .bind(ctx.uid, key, ...r, at)),
    // 推薦の控えを捨てる（work_piece のトリガーが rec_rev も進める）
    ctx.db.prepare('DELETE FROM rec_cache WHERE user_id=?').bind(ctx.uid)]);
  return {body: {ok: true, work_key: key, n: rows.length}};
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
  // 作品ごとの出演者（work_piece.cast_in）も前の公演の名前なので、全員に戻す
  await ctx.db.batch([ctx.db.prepare("UPDATE works SET stage_auto=0, stage_off=?, cast_off='' WHERE user_id=? AND work_key=?")
    .bind(stageId ? 0 : 1, ctx.uid, workKey),
  ctx.db.prepare("UPDATE work_piece SET cast_in='' WHERE user_id=? AND work_key=? AND cast_in<>''").bind(ctx.uid, workKey)]);
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
  let ws = await loadWorks(ctx);
  if ((await autoMerge(ctx, ws)).length) ws = await loadWorks(ctx);
  const seen = ws.filter(w => !w.unseen);
  const d = {seen, nSkip: ws.length - seen.length, nRated: seen.filter(w => w.verdict).length,
    nNotes: seen.filter(w => strip(w.note_impression || '')).length};
  const people = await peopleByKey(ctx, ws);
  let year = qsFirst(params, 'y'), group = qsFirst(params, 'g', 'work'), page = pageOf(params);
  const want = qsFirst(params, 'w');
  const check = ws.filter(w => w.suspect);
  let rest = ws.filter(w => !w.suspect && !w.unseen);
  // app._flatten_visits: a manual record has no mails to open, so only the order changes.
  // まとめた記録は、観た回ごとの行に開く（起案者の問い 2026-10-21。前はまとめた回が消え、説明の「行った日の数だけ並びます」と食い違った）。
  // 評価・感想は残した記録のものを共有する。直す欄は残した回の行にだけ付ける
  const restVisit = sortBy(rest.flatMap(w => !(w.merged || []).length ? [w] : visitsOf(w).map((v, i) => ({...w,
    first_date: v.date, last_date: v.last_date, time: v.time, venue: v.venue, stage_id: v.stage_id || w.stage_id,
    times: v.times, merged: [], visits: [v], seen_times: v.times, visitOf: v.kept ? '' : `-v${i}`}))), w => w.first_date || '0000', true);
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
    {poster: posterHtml(w, files), editable: !w.visitOf, idSuffix: w.visitOf || '', label: labels[w.stage_id] || '', scale, fullDate: true})).join('');
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
    link_stage: linkStageAction, visit_note: visitNoteAction, unseen: unseenAction, cast_seen: castSeenAction, pieces: piecesAction},
};
