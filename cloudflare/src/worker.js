import {isOriginalRoute, originalUI, ORIGINAL_SCREENS, ORIGINAL_WRITES} from './original-ui.js';
import {verifyIdToken, isAuthError} from './firebase-auth.js';
import {passkeyRoutes} from './passkey.js';
import {scoreFromIndex, d1Access, gradeOf, seedsFromFavourites, collapseRanked, cleanAspects, SEED_KINDS, SEED_ROLES, MAX_SEED_FAVS, cmp} from './recommend.js';
import {searchIndex, d1Search} from './stage-search.js';
import {suggest} from './screens/suggest.js';
import {exportPayload} from './screens/settings.js';
import {chooseVariant} from './reco-gate.js';
import {R2_READS_CAP, r2ReadAllowed, d1RoomLeft, d1Bytes, D1_BYTES_CAP, MAX_ACCOUNTS} from './free-tier.js';
import {rateLimit, checkNewAccount} from './rate-limit.js';
// Writes that only remove a user's rows: allowed even when D1 is at its storage cap.
const SHRINKING_ACTIONS = new Set(['drop_work', 'purge_work', 'unseen']);
const STORAGE_FULL = 'いまは保存を止めています（無料の範囲で動かすため、保存できる量の上限に近づいています）。見ることと消すことはできます。';
import {fetchCalendar} from './screens/import.js';
import {SCREEN_TABLES, nativeScreen, nativeAction, allNative, movingScreen, movingAction, screen as nativeScreenBody, action as nativeActionBody, readInput as nativeInput} from './screens/index.js';
const MAX_BODY = 262144;
const COOKIE = 'taguri_session';
const TTL = 60 * 60 * 24 * 30;
const json = (value, status = 200, headers = {}) => Response.json(value, {status, headers: {'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', ...headers}});
const fail = (status, message) => { throw Object.assign(new Error(message), {status}); };
const token = () => Array.from(crypto.getRandomValues(new Uint8Array(32)), b => b.toString(16).padStart(2,'0')).join('');
const hash = async s => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s))), b => b.toString(16).padStart(2,'0')).join('');
const now = () => Math.floor(Date.now() / 1000);
// SameSite=Lax, not Strict (起案者 2026-10-14「開き直すたびにログイン求められるのなぜ？」):
// with Strict the browser leaves the cookie off a page opened from another site or app
// (a link in LINE, mail, a chat), so the gate sent a signed-in person to /login every
// time. Lax sends it on such top-level GETs only; a POST from another site still
// carries no cookie, and every write here also checks Origin (CSRF, dec-session-lax).
const cookie = value => `${COOKIE}=${value}; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=${TTL}`;
function string(value, max, required = false) {
  if (typeof value !== 'string' || value.length > max || (required && !value.trim())) fail(400, '入力を確認してください。');
  return value.trim();
}
function record(value) {
  if (!value || typeof value !== 'object') fail(400, '記録を確認してください。');
  const r = {id: string(value.id ?? crypto.randomUUID(), 100, true), title: string(value.title, 500, true), date: string(value.date, 10, true), time: string(value.time ?? '', 5), venue: string(value.venue ?? '', 300), rating: string(value.rating ?? '', 5), note: string(value.note ?? '', 4000), stage_id: string(value.stage_id ?? '', 100)};
  if (r.stage_id && !/^[A-Za-z0-9_-]+$/.test(r.stage_id)) fail(400,'公演の結び付けを確認してください。');
  const parsed = new Date(`${r.date}T00:00:00Z`);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(r.date) || Number.isNaN(parsed.getTime()) || parsed.toISOString().slice(0,10) !== r.date) fail(400,'日付を確認してください。');
  if (r.time && !/^([01]\d|2[0-3]):[0-5]\d$/.test(r.time)) fail(400,'時刻を確認してください。');
  // ◎○△× or "value/levels" on a scale the user chose (2–11 levels, e.g. "4/5").
  if (r.rating && !gradeOf(r.rating)) fail(400,'評価を確認してください。');
  // 詳細: "code" = a trouble, "+code" = good; known codes only, stored as
  // comma-separated text in a fixed order. An array, or the text /api/state returns.
  const raw = value.aspects ?? [];
  if (!(Array.isArray(raw) ? raw.length <= 16 && raw.every(a => typeof a === 'string') : typeof raw === 'string' && raw.length <= 200)) fail(400,'詳細を確認してください。');
  r.aspects = cleanAspects(raw);
  if (r.aspects === null) fail(400,'詳細を確認してください。');
  return r;
}
function favourite(value) {
  const f = {name: string(value?.name, 200, true), kind: string(value?.kind, 20, true)};
  if (!['人','団体','主催','作品','題材','原作者'].includes(f.kind)) fail(400, '種類を確認してください。');
  return f;
}
function reaction(value) {
  const r={stage_id:string(value?.stage_id,100,true),status:string(value?.status,10,true)};
  if(!['interest','no','owned'].includes(r.status))fail(400,'反応を確認してください。');
  return r;
}
function reactionUpsert(db,uid,r) {
  return db.prepare('INSERT INTO reactions(user_id,stage_id,status,updated_at) VALUES(?,?,?,?) ON CONFLICT(user_id,stage_id) DO UPDATE SET status=excluded.status,updated_at=excluded.updated_at').bind(uid,r.stage_id,r.status,now());
}
async function body(request) {
  if (!request.headers.get('content-type')?.startsWith('application/json')) fail(415,'JSON形式で送信してください。');
  const reader = request.body?.getReader();
  if (!reader) fail(400,'入力がありません。');
  let size = 0; const chunks = [];
  while (true) { const {done,value} = await reader.read(); if (done) break; size += value.byteLength; if (size > MAX_BODY) { await reader.cancel(); fail(413,'ファイルが大きすぎます。'); } chunks.push(value); }
  const bytes = new Uint8Array(size); let offset = 0;
  for (const chunk of chunks) {bytes.set(chunk,offset); offset += chunk.length;}
  let value; try {value=JSON.parse(new TextDecoder().decode(bytes));} catch {fail(400,'JSONを読み取れませんでした。');}
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail(400,'JSONの形式を確認してください。');
  return value;
}
const sessionCookie = request => request.headers.get('cookie')?.match(/(?:^|;\s*)taguri_session=([a-f0-9]{64})(?:;|$)/)?.[1];
async function user(request, db) {
  const raw = sessionCookie(request);
  if (!raw) fail(401,'復旧コードでログインするか、新しく始めてください。');
  const session = await db.prepare('SELECT user_id FROM sessions WHERE hash=? AND expires_at>?').bind(await hash(raw),now()).first();
  if (!session) fail(401,'ログインし直してください。');
  return session.user_id;
}
// The signed-in user, or null (never throws for a missing/expired session).
async function currentUser(request, db) {
  const raw = sessionCookie(request);
  if (!raw) return null;
  return (await db.prepare('SELECT user_id FROM sessions WHERE hash=? AND expires_at>?').bind(await hash(raw),now()).first())?.user_id ?? null;
}
// New session for uid; the caller's old session (if any) is revoked so a
// session fixed before sign-in cannot carry over (session rotation).
async function startSession(db, uid, commands, oldRaw) {
  const session = token();
  if (oldRaw) commands.push(db.prepare('DELETE FROM sessions WHERE hash=?').bind(await hash(oldRaw)));
  // Delete expired sessions and bound the number of devices per account.
  commands.push(db.prepare('DELETE FROM sessions WHERE user_id=? AND (expires_at<=? OR hash NOT IN (SELECT hash FROM sessions WHERE user_id=? ORDER BY expires_at DESC LIMIT 9))').bind(uid,now(),uid));
  commands.push(db.prepare('INSERT INTO sessions(hash,user_id,expires_at,created_at) VALUES(?,?,?,?)').bind(await hash(session),uid,now()+TTL,now()));
  await db.batch(commands);
  return session;
}
// A sign-in made within REAUTH_SEC on this device. Irreversible or lasting
// changes (deleting the account, adding a passkey, linking Google or an email)
// need one, so a stolen long-lived cookie alone cannot make them.
const REAUTH_SEC = 600;
async function freshSession(db, request, uid) {
  const raw = sessionCookie(request);
  if (!raw) return false;
  const session = await db.prepare('SELECT created_at FROM sessions WHERE hash=? AND user_id=?').bind(await hash(raw),uid).first();
  return Boolean(session?.created_at) && session.created_at >= now() - REAUTH_SEC;
}
// Sign in with a Firebase ID token. Only the Firebase UID is kept.
// - known UID: sign in to that account
// - unknown UID with {link:true} (the account page's "結び付ける", sent only
//   from the browser that asked for it) while freshly signed in to an account
//   with no Firebase link yet: link it, so existing records carry over
// - unknown UID while signed in to an unlinked account without {link:true}:
//   refused, so signing in on a shared device never links someone else's
//   account and never silently starts a new one
// - otherwise: create a new account (if registration is open)
// Two existing accounts are never merged automatically.
async function firebaseSignIn(request, env) {
  const input = await body(request);
  let identity;
  try { identity = await verifyIdToken(input.id_token, env.FIREBASE_PROJECT_ID); }
  catch (e) {
    if (e.config) fail(503,'ログインの準備ができていません。');
    if (isAuthError(e)) fail(401,'ログインを確認できませんでした。もう一度ログインしてください。');
    throw e;
  }
  const db = env.DB, oldRaw = sessionCookie(request);
  let uid = (await db.prepare('SELECT id FROM users WHERE firebase_uid=?').bind(identity.uid).first())?.id;
  let linked = false, created = false;
  const commands = [];
  const current = oldRaw ? await db.prepare('SELECT u.id,u.firebase_uid,s.created_at FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.hash=? AND s.expires_at>?').bind(await hash(oldRaw),now()).first() : null;
  if (input.link === true) {
    if (!current) fail(401,'結び付けるアカウントでログインしていません。ログインしてから、もう一度アカウントのページから進んでください。');
    if (uid && uid !== current.id) fail(409,'この Google・メールは、すでに別のアカウントで使われています。結び付けられませんでした。');
    if (!uid) {
      if (current.firebase_uid) fail(409,'このアカウントには、すでに別の Google・メールが結び付いています。');
      if (!current.created_at || current.created_at < now() - REAUTH_SEC) fail(401,'本人確認のため、復旧コードかパスキーでログインし直してから、10分以内に結び付けてください。');
      uid = current.id; linked = true;
      commands.push(db.prepare('UPDATE users SET firebase_uid=? WHERE id=? AND firebase_uid IS NULL').bind(identity.uid,uid));
    }
  } else if (!uid && current && !current.firebase_uid) {
    fail(409,'いまログインしているアカウントの記録を引き継ぐには、アカウントのページの「Google・メールを結び付ける」から進んでください。別のアカウントとして始めるなら、ログアウトしてからログインしてください。');
  }
  if (!uid) {
    if (env.ALLOW_REGISTRATION !== 'true') fail(503,'新規登録を一時停止しています。');
    await checkNewAccount(db, env, fail);
    uid = crypto.randomUUID(); created = true;
    commands.push(db.prepare('INSERT INTO users(id,recovery_hash,created_at,firebase_uid) VALUES(?,?,?,?)').bind(uid,'firebase:'+token(),now(),identity.uid));
  }
  const session = await startSession(db, uid, commands, oldRaw);
  return json({linked,created},200,{'Set-Cookie':cookie(session)});
}
// Account deletion (security rules R7). Irreversible, so it needs a fresh
// sign-in (freshSession). Every table is cleared explicitly rather than
// relying on foreign-key cascades. The Firebase user (Google side) is deleted
// by the browser right after, while it still holds a fresh Firebase sign-in.
async function deleteAccount(request, env, uid, input) {
  if (input.confirm !== '削除') fail(400,'確認のため「削除」と入力してください。');
  if (!await freshSession(env.DB, request, uid)) fail(401,'本人確認のため、ログインし直してから削除してください。');
  const linked = (await env.DB.prepare('SELECT firebase_uid FROM users WHERE id=?').bind(uid).first())?.firebase_uid;
  // The browser can delete the Google-side user only while it holds a fresh
  // Firebase sign-in, so a linked account must be deleted after signing in
  // with Google or the email link (otherwise the email would stay at Google).
  if (linked && input.firebase_ready !== true) fail(409,'このアカウントは Google またはメールと結び付いています。Google 側の記録も消すため、Google かメールのリンクでログインし直してから削除してください。');
  await env.DB.batch(['records','favourites','reactions','passkeys','webauthn_challenges','rec_cache',...SCREEN_TABLES,'sessions']
    .map(t => env.DB.prepare(`DELETE FROM ${t} WHERE user_id=?`).bind(uid))
    .concat(env.DB.prepare('DELETE FROM users WHERE id=?').bind(uid)));
  return json({deleted:true,firebase_linked:!!linked},200,{'Set-Cookie':`${COOKIE}=; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=0`});
}
// ---------------------------------------------------------------- recommendations
// Person scores from the batch-built index (migrations/0003, scripts/
// build_recommend_index.py) and the user's own ratings. Same results as the
// Python recommender (test/recommend.test.js). Stages the user already reacted
// to (interest / no / owned) are left out, as the Python app moves them to
// other lists. Tour grouping and impression preferences are not ported yet.
const RECOMMEND_TOP = 15;
const RECOMMENDER = 'person-ordinal-v3+fav3+asp1+tour1+why1';   // +why1: a show needs a person who raised it; +fav3: favourites (people, troupes, works, subjects) as fading pseudo ratings; +asp1: 詳細; +tour1: one slot per tour
const jstToday = () => new Date(Date.now() + 9 * 3600 * 1000).toISOString().slice(0, 10);
// Served from rec_cache unless the index version, the date, or the user's
// records/reactions changed since it was computed (a few rows read per view).
export async function recommendFor(db, uid, today = jstToday()) {
  const ver = (await db.prepare("SELECT v FROM rec_meta WHERE k='current'").first())?.v;
  if (!ver) return {ready: false, items: []};
  const st = await db.prepare('SELECT (SELECT count(*) FROM records WHERE user_id=?1) AS rn, (SELECT max(updated_at) FROM records WHERE user_id=?1) AS rm, (SELECT count(*) FROM reactions WHERE user_id=?1) AS an, (SELECT max(updated_at) FROM reactions WHERE user_id=?1) AS am').bind(uid).first();
  // RECOMMENDER names the scoring rules: changing them must not serve old results.
  const stamp = [RECOMMENDER, ver, today, st.rn, st.rm, st.an, st.am].join('|');
  const cached = await db.prepare('SELECT body FROM rec_cache WHERE user_id=? AND stamp=?').bind(uid, stamp).first();
  if (cached) return {...JSON.parse(cached.body), cached: true};
  const body = await computeRecommendations(db, uid, ver, today);
  await db.prepare('INSERT INTO rec_cache(user_id,stamp,body,created_at) VALUES(?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET stamp=excluded.stamp,body=excluded.body,created_at=excluded.created_at')
    .bind(uid, stamp, JSON.stringify(body), now()).run();
  return {...body, cached: false};
}
async function computeRecommendations(db, uid, ver, today) {
  const records = (await db.prepare("SELECT id,rating,COALESCE(stage_id,'') AS stage_id,date,updated_at,aspects FROM records WHERE user_id=? AND rating<>''").bind(uid).all()).results;
  const access = d1Access(db, ver);
  const linked = [...new Set(records.map(r => r.stage_id).filter(Boolean))];
  const people = await access.peopleFor(linked);
  // updated_at is epoch seconds here; as text it orders like the Python timestamps.
  const rated = records.map(r => ({key: r.id, stage_id: r.stage_id, verdict: r.rating, date: r.date, aspects: r.aspects,
    updated_at: new Date(r.updated_at * 1000).toISOString(), people: people.get(r.stage_id) || []}));
  // 裏の答え合わせ: use a variant of the rules only if it clearly predicted
  // this user's own later ratings better (src/reco-gate.js). Kept out of the
  // answer shown on screen.
  const gate = chooseVariant(rated);
  // Favourite people's productions count as pseudo ratings that fade as real
  // ratings come in (q-favourites-seed); their own shows are left out here.
  const favourites = (await db.prepare('SELECT name,kind FROM favourites WHERE user_id=? ORDER BY kind,name LIMIT 200').bind(uid).all()).results;
  const {seeds, skip} = await seedsFromFavourites(access, favourites);
  const ranked = await scoreFromIndex({...access, rated: gate.aspects ? rated : rated.map(r => ({...r, aspects: []})),
    multipliers: gate.multipliers, today, seeds, skip});
  const reacted = new Set((await db.prepare('SELECT stage_id FROM reactions WHERE user_id=?').bind(uid).all()).results.map(r => r.stage_id));
  // One slot per production: a tour's other venues ride along with its
  // best-ranked one (user_recommender.collapse_tours), after reacted stages
  // are left out, as the Python screen does.
  const byId = new Map(ranked.map(c => [c.stage_id, c]));
  const top = collapseRanked(ranked.filter(c => !reacted.has(c.stage_id)), RECOMMEND_TOP);
  const entries = new Map();
  const ids = top.flatMap(g => [g.stage_id, ...g.tours]);
  for (let i = 0; i < ids.length; i += 98) {
    const chunk = ids.slice(i, i + 98);
    const rows = (await db.prepare(`SELECT stage_id,title,grp,start,end,entry FROM rec_stage WHERE ver=? AND stage_id IN (${chunk.map(() => '?').join(',')})`).bind(ver, ...chunk).all()).results;
    for (const r of rows) entries.set(r.stage_id, r);
  }
  const venue = id => {
    const e = entries.get(id) || {}, entry = JSON.parse(e.entry || '{}');
    return {stage_id: id, start: e.start || '', end: e.end || '', theater: entry.theater || '', pref: entry.pref || '', url: entry.url || ''};
  };
  return {ready: true, n_rated: records.length, n_linked: records.filter(r => people.get(r.stage_id)?.length).length,
    rows_read: access.counter.rows, variant: gate.variant, n_seeds: seeds.length, items: top.map(g => {
      const c = byId.get(g.stage_id), e = entries.get(g.stage_id) || {};
      return {...venue(g.stage_id), title: e.title || '', group: e.grp || '', score: c.b,
        // People first; kinds of show ("#形式" etc. as role) fill the rest of the 3 slots.
        reasons: [...c.parts.slice(0, 3), ...c.kinds].slice(0, 3).map(([, role, person, n]) => ({role, person, n})),
        tours: g.tours.map(venue)};
    })};
}
// How old the delivered catalogue is: dates and counts only, written by
// scripts/deliver_catalogue.py (tools/taguri/check_catalog_age.py reads it).
export async function health(db) {
  const rows = (await db.prepare("SELECT k,v FROM rec_meta WHERE k IN ('catalogue_scan','catalogue_delivered','catalogue_upcoming')").all()).results;
  const m = Object.fromEntries(rows.map(r => [r.k, r.v]));
  const catalog = {present: Boolean(m.catalogue_delivered)};
  if (m.catalogue_delivered) catalog.uploaded_at = m.catalogue_delivered;
  if (m.catalogue_scan) catalog.scan_date = m.catalogue_scan;
  catalog.upcoming = {candidates: Number(m.catalogue_upcoming || 0)};
  // Whether 開幕リマインド has anything to show: stages first playing in the next 14 days,
  // in the recommendation index (replaced only on days it fits the write budget) and in
  // the catalogue (upserted daily). Counts only, read through the start/date indexes.
  try {
    const today = new Date(Date.now() + 9 * 3600e3).toISOString().slice(0, 10);
    const hi = new Date(Date.parse(today) + 13 * 864e5).toISOString().slice(0, 10);
    const ver = (await db.prepare("SELECT v FROM rec_meta WHERE k='current'").first())?.v || '';
    const idx = ver ? (await db.prepare('SELECT count(*) n FROM rec_stage WHERE ver=? AND start>=? AND start<=?').bind(ver, today, hi).first())?.n || 0 : 0;
    const cat = (await db.prepare('SELECT count(*) n FROM catalogue WHERE date>=? AND date<=?').bind(today, hi).first())?.n || 0;
    catalog.opening_14d = {index: idx, catalogue: cat};
    if (ver) catalog.index_version = ver;
  } catch { /* tables not there yet */ }
  // Free-tier counters (docs/free-tier-budget.md): counts only, nothing about users.
  let r2Reads = null;
  try {
    r2Reads = (await db.prepare('SELECT n FROM usage WHERE k=?').bind(`r2_get:${new Date().toISOString().slice(0, 7)}`).first())?.n || 0;
  } catch { /* migration 0014 not applied yet */ }
  let accounts = null;
  try { accounts = (await db.prepare('SELECT count(*) AS n FROM users').first())?.n ?? null; } catch { /* no table */ }
  return {ok: true, catalog, free_tier: {r2_reads_month: r2Reads, r2_reads_cap: R2_READS_CAP,
    d1_bytes: await d1Bytes(db), d1_bytes_cap: D1_BYTES_CAP, accounts, accounts_cap: MAX_ACCOUNTS}};
}
// Stages for linking a record: ?q=title[&date=YYYY-MM-DD] searches by title,
// ?ids=a,b,... returns the linked stages' names. Public catalogue fields only.
export async function stagesFor(db, params) {
  const ver = (await db.prepare("SELECT v FROM rec_meta WHERE k='current'").first())?.v;
  if (!ver) return {ready: false, items: []};
  const access = d1Search(db, ver);
  let ids;
  if (params.has('ids')) {
    ids = [...new Set(params.get('ids').split(',').filter(Boolean))];
    if (ids.length > 100 || ids.some(id => !/^[A-Za-z0-9_-]{1,100}$/.test(id))) fail(400,'公演の指定を確認してください。');
  } else {
    const q = params.get('q') ?? '', date = params.get('date') ?? '';
    if (q.length > 100 || (date && !/^\d{4}-\d{2}-\d{2}$/.test(date))) fail(400,'検索する題名を確認してください。');
    ids = await searchIndex(access.entriesFor, q, date);
  }
  return {ready: true, items: await access.stages(ids)};
}
// Past stages to ask a new user about first (q-first-rating-onboarding): the
// favourites' stages that have already opened, then the batch's list of
// stages covering the coming catalogue (build_recommend_index.onboarding_list),
// leaving out stages the user has already recorded. Which screen asks, and
// only on the first rating, is up to the screens.
const ONBOARDING_TOP = 20;
export async function onboardingFor(db, uid, today = jstToday()) {
  const ver = (await db.prepare("SELECT v FROM rec_meta WHERE k='current'").first())?.v;
  if (!ver) return {ready: false, items: []};
  let listed = [];
  try {
    const meta = JSON.parse((await db.prepare("SELECT v FROM rec_meta WHERE k='onboarding'").first())?.v || '{}');
    if (meta.ver === ver && Array.isArray(meta.ids)) listed = meta.ids.filter(id => typeof id === 'string');
  } catch { listed = []; }
  const access = d1Access(db, ver);
  const favourites = (await db.prepare('SELECT name,kind FROM favourites WHERE user_id=? ORDER BY kind,name LIMIT 200').bind(uid).all()).results;
  const names = [...new Set(favourites.filter(f => SEED_KINDS.includes(f.kind)).map(f => f.name))].sort(cmp).slice(0, MAX_SEED_FAVS);
  const favSids = names.length ? [...new Set((await access.postingsFor(names.flatMap(n => SEED_ROLES.map(role => [role, n])))).map(r => r[2]))].sort(cmp) : [];
  const runs = await access.stagesFor(favSids);
  const opened = favSids.filter(sid => runs.get(sid)?.start && runs.get(sid).start <= today);
  const recorded = new Set((await db.prepare('SELECT stage_id FROM records WHERE user_id=? AND stage_id IS NOT NULL').bind(uid).all()).results.map(r => r.stage_id));
  const fav = new Set(opened);
  const ids = [...new Set([...opened, ...listed])].filter(sid => !recorded.has(sid)).slice(0, ONBOARDING_TOP);
  const items = await d1Search(db, ver).stages(ids);
  return {ready: true, items: items.map(i => ({...i, because: fav.has(i.stage_id) ? 'favourite' : 'catalogue'}))};
}
function upsert(db, uid, r) {
  return db.prepare('INSERT INTO records(user_id,id,title,date,time,venue,rating,note,stage_id,aspects,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(user_id,id) DO UPDATE SET title=excluded.title,date=excluded.date,time=excluded.time,venue=excluded.venue,rating=excluded.rating,note=excluded.note,stage_id=excluded.stage_id,aspects=excluded.aspects,updated_at=excluded.updated_at').bind(uid,r.id,r.title,r.date,r.time,r.venue,r.rating,r.note,r.stage_id||null,r.aspects,now());
}
async function state(db, uid) {
  const result = await db.batch([db.prepare("SELECT id,title,date,time,venue,rating,note,COALESCE(stage_id,'') AS stage_id,aspects FROM records WHERE user_id=? ORDER BY date DESC,id LIMIT 500").bind(uid),db.prepare('SELECT name,kind FROM favourites WHERE user_id=? ORDER BY kind,name LIMIT 200').bind(uid),db.prepare('SELECT stage_id,status FROM reactions WHERE user_id=? ORDER BY stage_id LIMIT 500').bind(uid)]);
  return {version:2,records:result[0].results,favourites:result[1].results,reactions:result[2].results};
}
const passkey = passkeyRoutes({fail, json, token, hash, now, body, cookie, sessionCookie, currentUser, startSession, checkNewAccount, freshSession});
// Public Firebase web config. apiKey identifies the project to Google; it is
// not a secret (access is governed by authorized domains and the sign-in
// methods enabled in the console). Nothing here is read from user input.
function firebaseConfig(env) {
  if (!env.FIREBASE_API_KEY || !env.FIREBASE_PROJECT_ID) return null;
  return {apiKey: env.FIREBASE_API_KEY, projectId: env.FIREBASE_PROJECT_ID,
          authDomain: env.FIREBASE_AUTH_DOMAIN || `${env.FIREBASE_PROJECT_ID}.firebaseapp.com`};
}
// /login is the only page allowed to talk to Google's sign-in endpoints; every
// other page keeps the site-wide policy in public/_headers. The popup flow loads
// apis.google.com/js/api.js and frames the project's auth domain; reCAPTCHA
// (phone sign-in only) stays blocked.
async function loginPage(request, env) {
  const config = firebaseConfig(env);
  const asset = await env.ASSETS.fetch(new Request(new URL('/login', request.url), request));
  const headers = new Headers(asset.headers);
  const authOrigin = config ? `https://${config.authDomain}` : '';
  headers.set('Content-Security-Policy', ["default-src 'self'", "script-src 'self' https://apis.google.com", "style-src 'self'", "img-src 'self' data:",
    "connect-src 'self' https://identitytoolkit.googleapis.com https://securetoken.googleapis.com",
    `frame-src ${authOrigin || "'none'"}`, "base-uri 'none'", "form-action 'self'", "frame-ancestors 'none'", "object-src 'none'"].join('; '));
  headers.set('Referrer-Policy', 'no-referrer');
  headers.set('X-Content-Type-Options', 'nosniff');
  headers.set('X-Frame-Options', 'DENY');
  headers.set('Cache-Control', 'no-store');
  const page = new Response(asset.body, {status: asset.status, headers});
  // The top of /login explains what たぐり is (it was /about). Re-signing in to
  // delete the account or to link Google/email is not the place for it: those
  // pages drop the section.
  const q = new URL(request.url).searchParams;
  if ((q.get('purpose') === 'delete' || q.get('link') === '1') && typeof HTMLRewriter !== 'undefined')
    return new HTMLRewriter().on('#about', {element(el) { el.remove(); }}).transform(page);
  return page;
}
// ---------------------------------------------------------------- sign-in gate
// Signed-out visitors may see only /login (which now also explains what たぐり
// is; /about moved there) and the static files it needs. Every other page
// sends them to sign in; the original screens' data answers 401.
const PUBLIC_PAGES = new Set(['/login', '/about']);   // /about only redirects to /login
// APIs that start a session (or hold no user data) must work before sign-in.
const PUBLIC_APIS = new Set(['/api/register', '/api/recover', '/api/catalogue', '/api/health']);
const STATIC_FILE = /\.(css|js|mjs|map|png|jpe?g|gif|webp|svg|ico|mp4|webmanifest|txt)$/;
// Only same-site paths are accepted as a place to return to after sign-in.
// Browsers drop tabs/newlines and read "\" as "/" in URLs, so "/\t/evil" or
// "/\evil" would leave the site: the value is parsed as a URL and must stay
// on this origin; control characters and backslashes are refused outright.
export const safeNext = value => {
  if (typeof value !== 'string' || !value.startsWith('/') || /[\u0000-\u001f\u007f\\]/.test(value)) return '/';
  let url;
  try { url = new URL(value, 'https://taguri.invalid'); } catch { return '/'; }
  if (url.origin !== 'https://taguri.invalid' || url.pathname.startsWith('/login')) return '/';
  return url.pathname + url.search + url.hash;
};
const redirect = location => new Response(null, {status: 302, headers: {Location: location, 'Cache-Control': 'no-store'}});
// The code of 「公演情報の登録」① (calendar and mail import), loaded only on that screen.
// Done here (not in web/, shared with the GitHub Pages demo) with HTMLRewriter.
// (The menu's 「アカウント・記録」 link to the older /migration-data/ page is gone: the
// menu has its own アカウント page, 起案者 2026-10-14「不要なら削除」.)
function withWorkerParts(response) {
  if (!(response.headers.get('content-type') || '').includes('text/html') || typeof HTMLRewriter === 'undefined') return response;
  return new HTMLRewriter().on('body', {element(el) {
    el.append('<script type="module" src="/vendor/import-loader.js"></script>', {html: true});
  }}).transform(response);
}
// Screens and writes of the original UI already ported to the Worker
// (src/screens/). Signed-in only: gate() has already sent everyone else away.
async function nativeRoute(request, env, url) {
  if (allNative(env) && request.method === 'GET' && url.pathname === '/export.json') {
    try {
      const uid = await user(request, env.DB);
      const body = JSON.stringify(await exportPayload({db: env.DB, uid}), null, 1);
      return new Response(body, {headers: {'Content-Type': 'application/json; charset=utf-8', 'Content-Disposition': 'attachment; filename="taguri-export.json"', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'}});
    } catch (error) {
      return json({ok:false,error:error.status ? error.message : '書き出せませんでした。'}, error.status ?? 500);
    }
  }
  if (allNative(env) && request.method === 'GET' && ['/api/suggest', '/api/suggest_web'].includes(url.pathname)) {
    try {
      const uid = await user(request, env.DB);
      return json(await suggest(url.searchParams, {db: env.DB, uid, today: env.CLOCK?.today ?? jstToday(), now: env.CLOCK?.now ?? Date.now()}));
    } catch (error) {
      return json({ok:false,error:error.status ? error.message : '探せませんでした。'}, error.status ?? 500);
    }
  }
  const m = url.pathname.match(/^\/api\/(?:screen\/([a-z]+)|([a-z_]+(?:\/[a-z_]+)?))$/);
  if (!m) return null;
  const isScreen = Boolean(m[1]) && request.method === 'GET';
  const isAction = Boolean(m[2]) && request.method === 'POST';
  if (!(isScreen ? nativeScreen(env, m[1]) : isAction && nativeAction(env, m[2]))) {
    // After the switch (NATIVE_UI=all) nothing of the original UI goes to Render any
    // more: a screen not ported yet says so, a write not ported yet is refused. The
    // Worker's own APIs with the same path (/api/recover) are left to the code below.
    if (!allNative(env)) return null;
    const moving = isScreen ? ORIGINAL_SCREENS.has(m[1]) : isAction && ORIGINAL_WRITES.has(url.pathname) && url.pathname !== '/api/recover';
    if (!moving) return null;
    try { await user(request, env.DB); } catch (error) { return json({ok:false,error:error.message}, error.status ?? 401); }
    if (isScreen) return json(movingScreen(m[1]));
    const out = movingAction();
    return json(out.body, out.status);
  }
  try {
    const uid = await user(request, env.DB);
    // env.CLOCK exists only in tests (an object cannot come from wrangler vars).
    const ctx = {db: env.DB, uid, today: env.CLOCK?.today ?? jstToday(), now: env.CLOCK?.now ?? Date.now()};
    if (isScreen) return json(await nativeScreenBody(m[1], url.searchParams, ctx));
    if (request.headers.get('origin') !== url.origin) fail(403,'同じサイトから操作してください。');
    if (!(request.headers.get('content-type') || '').startsWith('application/json')) fail(415,'JSONで送ってください。');
    const read = await nativeInput(request, m[2]);
    if (!read.input) return json(read.body, read.status);
    if (!SHRINKING_ACTIONS.has(m[2]) && !(await d1RoomLeft(env.DB, env))) fail(503, STORAGE_FULL);
    const out = await nativeActionBody(m[2], read.input, ctx);
    return json(out.body, out.status);
  } catch (error) {
    return json({ok:false,error:error.status ? error.message : '画面の読み込みに失敗しました。'}, error.status ?? 500);
  }
}
// After the switch only posters not yet in R2 still come from Render (no one's records).
const stillBridged = path => path.startsWith('/img/');
async function gate(request, env, url) {
  const path = url.pathname;
  if (path.startsWith('/api/auth/') || path.startsWith('/migration-api/') || PUBLIC_PAGES.has(path) || PUBLIC_APIS.has(path)) return null;
  if (path.startsWith('/vendor/') || path.startsWith('/assets/') || (STATIC_FILE.test(path) && !path.startsWith('/img/'))) return null;
  if (await currentUser(request, env.DB)) return null;
  const page = request.method === 'GET' && !path.startsWith('/api/') && !path.startsWith('/img/');
  if (!page) return json({error:'ログインしてください。'}, 401);
  if (path === '/') return redirect('/login');
  return redirect('/login?next=' + encodeURIComponent(path + url.search));
}
/**
 * GET /img/<file>: a poster from R2 (the POSTERS bucket, filled by the crawler's
 * scripts/deliver_posters.py). Only signed-in users get here (gate). A file not
 * in R2, or no bucket bound, falls through to the Render bridge as before.
 */
async function posterFromR2(request, env, url) {
  const m = /^\/img\/([A-Za-z0-9_.-]{1,80})$/.exec(url.pathname);
  if (!m || request.method !== 'GET' || !env.POSTERS) return null;
  if (!(await r2ReadAllowed(env))) return null;
  const obj = await env.POSTERS.get(m[1]);
  if (!obj) return null;
  // A poster file never changes once it is in R2 (deliver_posters.py uploads each stage once).
  const headers = new Headers({'Cache-Control': 'private, max-age=604800, immutable', 'X-Content-Type-Options': 'nosniff'});
  headers.set('Content-Type', obj.httpMetadata?.contentType || (/\.png$/i.test(m[1]) ? 'image/png' : 'image/jpeg'));
  if (obj.httpEtag) headers.set('ETag', obj.httpEtag);
  return new Response(obj.body, {headers});
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const limited = await rateLimit(request, env, url);
    if (limited) return limited;
    const blocked = await gate(request, env, url);
    if (blocked) return blocked;
    // たぐりとは and ログイン are one page now; old links to /about still land there.
    if (url.pathname === '/about') return redirect('/login');
    if (url.pathname === '/login' && request.method === 'GET') return loginPage(request, env);
    const poster = await posterFromR2(request, env, url);
    if (poster) return poster;
    // The Worker's own health (catalogue date, free-tier counters) even while the
    // Render bridge serves the other /api/ paths: catalog-age.yml and the crawler watch it.
    if (url.pathname === '/api/health' && request.method === 'GET') return json(await health(env.DB),200,{'Cache-Control':'public, max-age=300'});
    const migrationAPI=url.pathname.startsWith('/migration-api/');
    const native = await nativeRoute(request, env, url);
    if (native) return native;
    if(env.ORIGINAL_UI_BRIDGE==='true' && !migrationAPI && isOriginalRoute(url.pathname) && (!allNative(env) || stillBridged(url.pathname)))return originalUI(request);
    if(migrationAPI)url.pathname=url.pathname.replace('/migration-api/','/api/');
    // After the switch the menu has its own アカウント page (screens/account.js); the
    // older 「アカウント・記録」 page (/migration-data/) keeps only the passkey settings.
    if (!url.pathname.startsWith('/api/')) return withWorkerParts(await env.ASSETS.fetch(request));
    try {
      const path = url.pathname; const method = request.method;
      if (method !== 'GET' && method !== 'POST') fail(405,'対応していない操作です。');
      if (method === 'POST' && request.headers.get('origin') !== url.origin) fail(403,'同じサイトから操作してください。');
      if (method === 'GET' && path === '/api/health') return json(await health(env.DB),200,{'Cache-Control':'public, max-age=300'});
      if (method === 'GET' && path === '/api/catalogue') {
        // Public catalogue only: never include an owner's ranking or private reasons.
        const rows = await env.DB.prepare('SELECT id,title,date,venue,url,metadata FROM catalogue WHERE date>=? ORDER BY date,id LIMIT 1000').bind(new Date(Date.now()-30*86400000).toISOString().slice(0,10)).all();
        const items=rows.results.map(({metadata,...c})=>{const m=JSON.parse(metadata);return {...c,group:m.group??'',fields:m.fields??{},synopsis:m.synopsis??'',words:m.words??[],end_date:m.end_date??c.date};});
        return json({items},200,{'Cache-Control':'public, max-age=300'});
      }
      if (method === 'POST' && ['/api/register','/api/recover'].includes(path)) {
        const input = await body(request);
        let uid; let recovery;
        if (path === '/api/register') {
          if (env.ALLOW_REGISTRATION !== 'true') fail(503,'新規登録を一時停止しています。');
          await checkNewAccount(env.DB, env, fail);
          recovery = token(); uid = crypto.randomUUID();
        } else {
          const code = string(input.code, 80, true).replaceAll('-', '').toLowerCase();
          if (!/^[a-f0-9]{64}$/.test(code)) fail(401,'復旧コードを確認してください。');
          uid = (await env.DB.prepare('SELECT id FROM users WHERE recovery_hash=?').bind(await hash(code)).first())?.id;
          if (!uid) fail(401,'復旧コードを確認してください。');
        }
        const commands = [];
        if (recovery) commands.push(env.DB.prepare('INSERT INTO users(id,recovery_hash,created_at) VALUES(?,?,?)').bind(uid,await hash(recovery),now()));
        const session = await startSession(env.DB, uid, commands, null);
        return json({recovery_code:recovery},200,{'Set-Cookie':cookie(session)});
      }
      if (method === 'POST' && path === '/api/auth/firebase') return await firebaseSignIn(request, env);
      if (method === 'POST' && path === '/api/auth/passkey/register/options') return await passkey.registerOptions(request, env);
      if (method === 'POST' && path === '/api/auth/passkey/register/verify') return await passkey.registerVerify(request, env);
      if (method === 'POST' && path === '/api/auth/passkey/login/options') return await passkey.loginOptions(request, env);
      if (method === 'POST' && path === '/api/auth/passkey/login/verify') return await passkey.loginVerify(request, env);
      if (method === 'GET' && path === '/api/auth/config') {
        const config = firebaseConfig(env);
        if (!config) fail(503,'ログインの準備ができていません。');
        return json(config,200,{'Cache-Control':'public, max-age=300'});
      }
      const uid = await user(request,env.DB);
      if (method === 'GET' && path === '/api/auth/passkeys') return await passkey.list(request, env, uid);
      if (method === 'POST' && path === '/api/auth/passkeys/delete') return await passkey.remove(request, env, uid);
      if (method === 'GET' && ['/api/state','/api/export'].includes(path)) return json(await state(env.DB,uid));
      if (method === 'GET' && path === '/api/recommend') return json(await recommendFor(env.DB, uid));
      if (method === 'GET' && path === '/api/stages') return json(await stagesFor(env.DB, url.searchParams));
      if (method === 'GET' && path === '/api/onboarding') return json(await onboardingFor(env.DB, uid));
      if (method !== 'POST') fail(404,'見つかりませんでした。');
      const input = await body(request);
      // Writes that change what is recommended drop the cached result (the stamp
      // alone misses two edits within the same second).
      if (path !== '/api/record/delete' && !(await d1RoomLeft(env.DB, env))) fail(503, STORAGE_FULL);
      if (['/api/record','/api/record/delete','/api/reaction','/api/favourite','/api/import'].includes(path))
        await env.DB.prepare('DELETE FROM rec_cache WHERE user_id=?').bind(uid).run();
      if (path === '/api/record') {
        const r = record(input);
        const existing = await env.DB.prepare('SELECT id FROM records WHERE user_id=? AND id=?').bind(uid,r.id).first();
        const count = (await env.DB.prepare('SELECT count(*) AS n FROM records WHERE user_id=?').bind(uid).first()).n;
        if (!existing && count >= 500) fail(409,'記録は500件まで保存できます。');
        await upsert(env.DB,uid,r).run(); return json({record:r});
      }
      if (path === '/api/record/delete') {
        await env.DB.prepare('DELETE FROM records WHERE user_id=? AND id=?').bind(uid,string(input.id,100,true)).run(); return json({ok:true});
      }
      if (path === '/api/favourite') {
        const f = favourite(input);
        if (input.remove === true) await env.DB.prepare('DELETE FROM favourites WHERE user_id=? AND name=? AND kind=?').bind(uid,f.name,f.kind).run();
        else {
          const count = (await env.DB.prepare('SELECT count(*) AS n FROM favourites WHERE user_id=?').bind(uid).first()).n;
          if (count >= 200) fail(409,'お気に入りは200件まで保存できます。');
          await env.DB.prepare('INSERT OR IGNORE INTO favourites(user_id,name,kind) VALUES(?,?,?)').bind(uid,f.name,f.kind).run();
        }
        return json({ok:true});
      }
      if (path === '/api/reaction') {
        const r = reaction(input);
        if (input.remove === true) await env.DB.prepare('DELETE FROM reactions WHERE user_id=? AND stage_id=?').bind(uid,r.stage_id).run();
        else await reactionUpsert(env.DB,uid,r).run();
        return json({ok:true});
      }
      if (path === '/api/import') {
        if (![1,2].includes(input.version) || !Array.isArray(input.records) || !Array.isArray(input.favourites) || input.records.length > 20 || input.favourites.length > 20) fail(400,'1回に記録20件・お気に入り20件まで取り込めます。');
        const signals = input.reactions ?? [];
        if (!Array.isArray(signals) || signals.length>20 || signals.length+input.records.length+input.favourites.length>40) fail(400,'1回に合計40項目まで取り込めます。');
        const rs = input.records.map(record), fs = input.favourites.map(favourite), reactions = signals.map(reaction);
        // Additive import, never erase an existing account or trust input user IDs.
        const existing = await state(env.DB,uid);
        if (new Set([...existing.records.map(r=>r.id),...rs.map(r=>r.id)]).size>500 || new Set([...existing.favourites,...fs].map(f=>JSON.stringify([f.name,f.kind]))).size>200 || new Set([...existing.reactions,...reactions].map(r=>r.stage_id)).size>500) fail(409,'保存件数の上限を超えています。');
        const commands = [...rs.map(r=>upsert(env.DB,uid,r)),...fs.map(f=>env.DB.prepare('INSERT OR IGNORE INTO favourites(user_id,name,kind) VALUES(?,?,?)').bind(uid,f.name,f.kind)),...reactions.map(r=>reactionUpsert(env.DB,uid,r))];
        if(commands.length) await env.DB.batch(commands);
        return json({ok:true,imported:rs.length});
      }
      if (path === '/api/calendar_ics') {
        // 「公演情報の登録」①: the browser reads the calendar itself (src/client/import.js).
        const got = await fetchCalendar(input.url);
        if (got.status !== 200) fail(got.status, got.error);
        return new Response(got.body, {headers: {'Content-Type': 'text/calendar; charset=utf-8', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'}});
      }
      if (path === '/api/account/delete') return await deleteAccount(request, env, uid, input);
      if (path === '/api/logout/all') {
        // Sign out every device, e.g. after losing a phone.
        await env.DB.prepare('DELETE FROM sessions WHERE user_id=?').bind(uid).run();
        return json({ok:true},200,{'Set-Cookie':`${COOKIE}=; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=0`});
      }
      if (path === '/api/logout') {
        const raw = request.headers.get('cookie')?.match(/taguri_session=([a-f0-9]{64})/)?.[1];
        await env.DB.prepare('DELETE FROM sessions WHERE hash=? AND user_id=?').bind(await hash(raw),uid).run();
        return json({ok:true},200,{'Set-Cookie':`${COOKIE}=; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=0`});
      }
      fail(404,'見つかりませんでした。');
    } catch (error) {
      // Do not expose SQL, private records, or environment configuration.
      return json({error:error.status ? error.message : '保存先に接続できませんでした。時間を置いてもう一度お試しください。'},error.status ?? 503);
    }
  }
};
