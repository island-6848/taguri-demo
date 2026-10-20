import {withCard, PREVIEW_BOT} from './link-card.js';
import {assetLinksResponse} from './app-links.js';
import {SESSION_TTL} from './session-policy.js';
import {deleteAccountStatements, sweepEmptyAccounts} from './cleanup.js';
import {purgeFixRequests} from './screens/fixrequest.js';
import {isOriginalRoute, originalUI, ORIGINAL_SCREENS, ORIGINAL_WRITES} from './original-ui.js';
import {verifyIdToken, isAuthError} from './firebase-auth.js';
import {passkeyRoutes} from './passkey.js';
import {TERMS_VERSION, requireAgreement, needsAgreement} from './terms.js';
import {d1Access, gradeOf, cleanAspects, SEED_KINDS, SEED_ROLES, MAX_SEED_FAVS, cmp} from './recommend.js';
import {recommendApi} from './screens/recommend.js';
import {searchIndex, d1Search} from './stage-search.js';
import {suggest, stageTimes} from './screens/suggest.js';
import {exportPayload} from './screens/settings.js';
import {R2_READS_CAP, r2ReadAllowed, d1RoomLeft, d1Bytes, D1_BYTES_CAP, MAX_ACCOUNTS} from './free-tier.js';
import {rateLimit, checkNewAccount, guardedUserInsert, countNewAccount, confirmNewAccount, rateLimitHealth} from './rate-limit.js';
// Writes that only remove a user's rows: allowed even when D1 is at its storage cap.
// 保存の上限でも通す操作（減らす操作と、既にある行を書き換えるだけの規約の同意 terms.agreeAction）
const SHRINKING_ACTIONS = new Set(['drop_work', 'purge_work', 'unseen', 'agree']);
// 中身で減らす操作か足す操作かが決まるもの（#88）。外す・消す・空にするときだけ通す。足すときは止めたまま
const SHRINKING_WHEN = {
  favourite: b => b.action === 'remove', decline: b => b.action === 'remove', kind_off: b => b.action === 'remove',
  ticket: b => b.action === 'del',
  // 表示名・アイコンを空にする（app_setting の行を消す）
  account: b => (Object.hasOwn(b, 'avatar') ? b.avatar === '' : b.display_name === ''),
};
/** 画面の書き込み（/api/<name>）が、保存の上限でも通してよい減らす操作か */
export const shrinkingAction = (name, input) => SHRINKING_ACTIONS.has(name) || Boolean(SHRINKING_WHEN[name]?.(input || {}));
// Worker の API で上限でも通すもの: 消す・外す操作と、ログアウト・アカウントの削除（セッションや行を消すだけ。#88）
// 復旧コードの作り直し（#126）は既にある行を書き換えるだけで増えない。漏れたコードを止める操作なので上限でも通す
const SHRINKING_PATHS = new Set(['/api/record/delete', '/api/logout', '/api/logout/all', '/api/account/delete', '/api/recovery/reissue']);
export const shrinkingPath = (path, input) => SHRINKING_PATHS.has(path)
  || (['/api/favourite', '/api/reaction'].includes(path) && input?.remove === true);
const STORAGE_FULL = '保存できる量の上限に近づいたので、無料の範囲で動かすために、いまは保存を止めています。見ることと消すことはできます。';
import {fetchCalendar} from './screens/import.js';
import {readCapped} from './body-limit.js';
import {nativeScreen, nativeAction, allNative, movingScreen, movingAction, screen as nativeScreenBody, action as nativeActionBody, readInput as nativeInput} from './screens/index.js';
const MAX_BODY = 262144;
const COOKIE = 'taguri_session';
const TTL = SESSION_TTL;
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
  if (!request.body) fail(400,'入力がありません。');
  const bytes = await readCapped(request, MAX_BODY);
  if (!bytes) fail(413,'ファイルが大きすぎます。');
  let value; try {value=JSON.parse(new TextDecoder().decode(bytes));} catch {fail(400,'JSONを読み取れませんでした。');}
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail(400,'JSONの形式を確認してください。');
  return value;
}
const sessionCookie = request => request.headers.get('cookie')?.match(/(?:^|;\s*)taguri_session=([a-f0-9]{64})(?:;|$)/)?.[1];
async function user(request, db) {
  const raw = sessionCookie(request);
  if (!raw) fail(401,'復旧コードでログインするか、新しく始めてください。');
  const session = await db.prepare('SELECT user_id FROM sessions WHERE hash=? AND expires_at>? AND created_at>?').bind(await hash(raw),now(),now()-TTL).first();
  if (!session) fail(401,'ログインし直してください。');
  return session.user_id;
}
// The signed-in user, or null (never throws for a missing/expired session).
async function currentUser(request, db) {
  const raw = sessionCookie(request);
  if (!raw) return null;
  return (await db.prepare('SELECT user_id FROM sessions WHERE hash=? AND expires_at>? AND created_at>?').bind(await hash(raw),now(),now()-TTL).first())?.user_id ?? null;
}
// New session for uid; the caller's old session (if any) is revoked so a
// session fixed before sign-in cannot carry over (session rotation).
// The session row goes in only when the user row exists: a new account's row is
// added earlier in the same batch only while the sign-up caps hold
// (rate-limit.guardedUserInsert, #124), so a refused sign-up leaves no session
// and keeps the device's old one.
// guard: [sql, ...args], a further condition on the users row (e.g. that the
// recovery code used is still the account's, #126; that the Firebase sign-in is
// newer than a sign-out everywhere, #178). The old session is revoked only when
// the new one goes in, so a refused sign-in keeps the device's old session.
async function startSession(db, uid, commands, oldRaw, guard = null) {
  const session = token();
  const [cond, ...args] = guard ?? ['1'];
  if (oldRaw) commands.push(db.prepare(`DELETE FROM sessions WHERE hash=? AND EXISTS (SELECT 1 FROM users WHERE id=? AND ${cond})`).bind(await hash(oldRaw),uid,...args));
  // Delete expired sessions and bound the number of devices per account.
  commands.push(db.prepare('DELETE FROM sessions WHERE user_id=? AND (expires_at<=? OR created_at IS NULL OR created_at<=? OR hash NOT IN (SELECT hash FROM sessions WHERE user_id=? ORDER BY expires_at DESC LIMIT 9))').bind(uid,now(),now()-TTL,uid));
  commands.push(db.prepare(`INSERT INTO sessions(hash,user_id,expires_at,created_at) SELECT ?,id,?,? FROM users WHERE id=? AND ${cond}`).bind(await hash(session),now()+TTL,now(),uid,...args));
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
// - unknown UID from the login box ({intent:'login'}): refused (sign up from the sign-up box)
// - otherwise: create a new account (if registration is open and the terms are agreed)
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
  const known = await db.prepare('SELECT id,tokens_valid_after FROM users WHERE firebase_uid=?').bind(identity.uid).first();
  // すべての端末でログアウトしたあとは、それより前のログインで得たトークンを受け付けない（#127）。
  // 新しく Google・メールでログインし直せば（auth_time が新しくなる）入れる
  if (known?.tokens_valid_after && identity.authTime <= known.tokens_valid_after)
    fail(401,'すべての端末でログアウトしたあとです。もう一度 Google かメールでログインしてください。');
  let uid = known?.id;
  let linked = false, created = false;
  const commands = [];
  const current = oldRaw ? await db.prepare('SELECT u.id,u.firebase_uid,s.created_at FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.hash=? AND s.expires_at>? AND s.created_at>?').bind(await hash(oldRaw),now(),now()-TTL).first() : null;
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
  if (!uid && input.link !== true && await firebaseDeletePending(db, identity.uid)) {
    // 前にたぐりのアカウントを削除したが、Google 側（Firebase）の利用者を消せなかった人（#128）。
    // セッションは作らない。ブラウザーはいまログインしたばかりなので、Firebase の利用者を消せる
    return json({firebase_delete_pending: true});
  }
  if (!uid) {
    // ログインの欄（intent: 'login'）から来たときは、新しいアカウントを作らない（起案者の指示 2026-10-17
    // 「ログイン（上）または新規登録（下）にレイアウトし直して」）。新規登録の欄は intent: 'signup'
    if (input.intent === 'login') fail(404,'この Google・メールは、まだ登録されていません。はじめての方は、下の「新規登録」から始めてください。');
    if (env.ALLOW_REGISTRATION !== 'true') fail(503,'新規登録を一時停止しています。');
    requireAgreement(input, fail);
    const plan = await checkNewAccount(db, env, fail, undefined, request);
    uid = crypto.randomUUID(); created = true;
    commands.push(guardedUserInsert(db, plan, ['id','recovery_hash','created_at','firebase_uid','terms_version','terms_at'], [uid,'firebase:'+token(),now(),identity.uid,TERMS_VERSION,now()]),
      ...countNewAccount(db, plan, uid));
  }
  // 上の失効の確認からここまでのあいだに /api/logout/all が終わっていたら、セッションを作らない（#178）。
  // 確認と作成のあいだの競合をなくすため、INSERT そのものに Firebase UID と失効時刻の条件を付け、
  // 行ができなかったら 401（成功の Cookie は返さない）。結び付け・新規作成は同じ batch で firebase_uid が入る
  const guard = known
    ? ['firebase_uid=? AND (tokens_valid_after IS NULL OR tokens_valid_after<?)', identity.uid, identity.authTime]
    : ['firebase_uid=?', identity.uid];
  const session = await startSession(db, uid, commands, oldRaw, guard);
  if (created) await confirmNewAccount(db, env, fail, uid, request);
  if (!(await db.prepare('SELECT 1 AS ok FROM sessions WHERE hash=?').bind(await hash(session)).first()))
    fail(401, known ? 'すべての端末でログアウトしたあとです。もう一度 Google かメールでログインしてください。' : 'ログインし直してください。');
  return json({linked,created},200,{'Set-Cookie':cookie(session)});
}
// Firebase 側の削除の保留（#128）。たぐりの記録を消したあと、Google 側（Firebase Authentication）の
// 利用者はブラウザーが消すが、失敗・離脱してもサーバーには分からない。そこで、結び付いていたアカウントを消すときに
// Firebase UID のハッシュだけを FIREBASE_DELETE_DAYS 日のあいだ usage に残す（UID そのもの・メールは残さない）。
// その間に同じ Google・メールでログインすると、セッションを作らずに「Google 側を消す」ようブラウザーに返す。
// ブラウザーの「消せた」という申告では消さない（サーバーでは確かめられないので、期限で消えるまで残す）。
const FIREBASE_DELETE_DAYS = 30;   // export しない: workerd は入り口の名前付き export をすべて入り口として読む
const firebaseDeleteKey = async firebaseUid => `fbdel:${await hash('firebase-uid|' + firebaseUid)}`;
async function firebaseDeletePending(db, firebaseUid) {
  return Boolean((await db.prepare('SELECT n FROM usage WHERE k=? AND n>?').bind(await firebaseDeleteKey(firebaseUid), now()).first())?.n);
}
async function firebaseDeleteStatements(db, firebaseUid) {
  return [db.prepare("DELETE FROM usage WHERE k LIKE 'fbdel:%' AND n<=?").bind(now()),
    db.prepare('INSERT INTO usage(k,n) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET n=excluded.n').bind(await firebaseDeleteKey(firebaseUid), now() + FIREBASE_DELETE_DAYS * 86400)];
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
  await env.DB.batch([...deleteAccountStatements(env.DB, uid), ...(linked ? await firebaseDeleteStatements(env.DB, linked) : [])]);
  // firebase_pending: Google 側はまだ消えていない（ブラウザーが消す。消せなければ、次のログインでもう一度）
  return json(linked ? {deleted:true,firebase_linked:true,firebase_pending:true} : {deleted:true,firebase_linked:false},200,{'Set-Cookie':`${COOKIE}=; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=0`});
}
// 復旧コードの作り直し（#126）。控えをなくした・人に見られたときに、アカウントと記録はそのままで、
// 古いコードだけを使えなくする。直近 10 分以内のログインが要る（盗まれた Cookie だけでは作り直せない）。
// 古いコードは 1 つの UPDATE で新しいコードに置き換わるので、同時に古いコードで入ろうとしても入れない
// （/api/recover はコードが変わっていないときだけセッションを作る）。この端末以外のセッションはすべて消す
// （古いコードで入った人を締め出すため）。Google・メールのリンク・パスキーはそのまま。
// Google・メールで始めたアカウント（復旧コードを持たない）は、新しくコードを作らない。
async function reissueRecovery(request, env, uid) {
  const db = env.DB;
  if (!await freshSession(db, request, uid)) fail(401,'本人確認のため、ログインし直してから10分以内に復旧コードを作り直してください。');
  const row = await db.prepare('SELECT recovery_hash FROM users WHERE id=?').bind(uid).first();
  if (!row || String(row.recovery_hash).startsWith('firebase:')) fail(409,'このアカウントには復旧コードがありません（Google・メールのリンクやパスキーでログインしてください）。');
  const recovery = token(), keep = await hash(sessionCookie(request));
  await db.batch([
    db.prepare("UPDATE users SET recovery_hash=? WHERE id=? AND substr(recovery_hash,1,9)<>'firebase:'").bind(await hash(recovery), uid),
    db.prepare('DELETE FROM sessions WHERE user_id=? AND hash<>?').bind(uid, keep)]);
  return json({recovery_code: recovery, other_sessions_signed_out: true});
}
// ---------------------------------------------------------------- recommendations
// GET /api/recommend answers with the recommendations of the 今週のおすすめ screen
// (screens/recommend.recommendApi: the same works / reactions / favourites, the same
// rules, the same rec_cache row), as plain data (#119). It used to compute another
// ranking from the migration-era tables (records / reactions), so what the user rated
// on the screens never reached it, and the two took turns overwriting rec_cache.
// The Python parity of the scoring itself is test/recommend.test.js (scoreFromIndex).
const jstToday = () => new Date(Date.now() + 9 * 3600 * 1000).toISOString().slice(0, 10);
export async function recommendFor(db, uid, today = jstToday(), nowMs = Date.now()) {
  return recommendApi({db, uid, today, now: nowMs});
}
// How old the delivered catalogue is: dates and counts only, written by
// scripts/deliver_catalogue.py (tools/taguri/check_catalog_age.py reads it).
export async function health(db, env = {}) {
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
  return {ok: true, catalog, rate_limit: rateLimitHealth(env), free_tier: {r2_reads_month: r2Reads, r2_reads_cap: R2_READS_CAP,
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
const passkey = passkeyRoutes({fail, json, token, hash, now, body, cookie, sessionCookie, currentUser, startSession, checkNewAccount, guardedUserInsert, countNewAccount, confirmNewAccount, freshSession});
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
    return withCard(new HTMLRewriter().on('#about', {element(el) { el.remove(); }}).transform(page), new URL(request.url));
  return withCard(page, new URL(request.url));
}
// 「Google カレンダーから取り込む」 comes back here with an access token in the
// address (#access_token=...). Only this page may call the Calendar API, from the
// browser; the token never reaches the Worker (the part after # is not sent).
async function calendarCallbackPage(request, env) {
  const asset = await env.ASSETS.fetch(new Request(new URL('/oauth-calendar', request.url), request));
  const headers = new Headers(asset.headers);
  headers.set('Content-Security-Policy', ["default-src 'self'", "script-src 'self'", "style-src 'self'", "img-src 'self'",
    "connect-src https://www.googleapis.com", "base-uri 'none'", "form-action 'none'", "frame-ancestors 'none'", "object-src 'none'"].join('; '));
  headers.set('Referrer-Policy', 'no-referrer');
  headers.set('Cache-Control', 'no-store');
  return new Response(asset.body, {status: asset.status, headers});
}
// ---------------------------------------------------------------- sign-in gate
// Signed-out visitors may see only /login (which now also explains what たぐり
// is; /about moved there) and the static files it needs. Every other page
// sends them to sign in; the original screens' data answers 401.
// /terms・/privacy は登録の前に読むので、ログインなしで開ける（public/terms.html・privacy.html）
const PUBLIC_PAGES = new Set(['/login', '/about', '/terms', '/privacy']);   // /about only redirects to /login
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
  // 観劇記録の追加で選んだ公演の、上演日ごとの開演時刻（screens/suggest.stageTimes）
  if (allNative(env) && request.method === 'GET' && url.pathname === '/api/stage_times') {
    try {
      await user(request, env.DB);
      return json(await stageTimes(url.searchParams, {db: env.DB}));
    } catch (error) {
      return json({ok:false,error:error.status ? error.message : '読めませんでした。'}, error.status ?? 500);
    }
  }
  // suggest_web も同じ保存済みの公演一覧から探す（その場で外のサイトは探さない。画面の文言もそう書く、#92）
  if (allNative(env) && request.method === 'GET' && ['/api/suggest', '/api/suggest_web'].includes(url.pathname)) {
    try {
      const uid = await user(request, env.DB);
      return json(await suggest(url.searchParams, {db: env.DB, uid, today: env.CLOCK?.today ?? jstToday(), now: env.CLOCK?.now ?? Date.now()}));
    } catch (error) {
      return json({ok:false,error:error.status ? error.message : '探せませんでした。'}, error.status ?? 500);
    }
  }
  // 画面は記録を足した・結び付けた直後に、裏の取得が終わったかを聞きに来る（web/app.js waitJob）。
  // Worker では裏で走る取得が無いので、いつも「走っていない」と答える。答えが無いと 404 になり、
  // 足すたびにブラウザーのコンソールにエラーが出ていた（#134 の通し検証）
  if (allNative(env) && request.method === 'GET' && url.pathname === '/api/import_status') {
    try { await user(request, env.DB); } catch (error) { return json({ok:false,error:error.message}, error.status ?? 401); }
    return json({running: false});
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
    const ctx = {db: env.DB, env, uid, today: env.CLOCK?.today ?? jstToday(), now: env.CLOCK?.now ?? Date.now()};
    if (isScreen) {
      const body = await nativeScreenBody(m[1], url.searchParams, ctx);
      // 規約の版が上がっていたら、画面が同意を求める（terms.agreeAction）
      if (body && typeof body === 'object' && await needsAgreement(env.DB, uid)) body.terms_update = TERMS_VERSION;
      return json(body);
    }
    if (request.headers.get('origin') !== url.origin) fail(403,'同じサイトから操作してください。');
    if (!(request.headers.get('content-type') || '').startsWith('application/json')) fail(415,'JSONで送ってください。');
    const read = await nativeInput(request, m[2]);
    if (!read.input) return json(read.body, read.status);
    if (!shrinkingAction(m[2], read.input) && !(await d1RoomLeft(env.DB, env))) fail(503, STORAGE_FULL);
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
  if (PREVIEW_BOT.test(request.headers.get('user-agent') || '')) return loginPage(request, env);
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
  // 1 日 1 回（wrangler.jsonc の triggers.crons）: 記録の無いアカウントを片付ける（cleanup.js）
  async scheduled(event, env, ctx) {
    ctx.waitUntil(sweepEmptyAccounts(env.DB).then(n => { if (n) console.log(`empty accounts removed: ${n}`); }));
    // 対応済みの公演修正依頼の本文・行を期限で消す（issue #129）
    ctx.waitUntil(purgeFixRequests(env.DB).then(r => { if (r.cleared || r.removed) console.log(`fix_request purged: ${r.cleared} bodies, ${r.removed} rows`); }));
  },
  async fetch(request, env) {
    const url = new URL(request.url);
    const limited = await rateLimit(request, env, url);
    if (limited) return limited;
    // Android アプリとの結び付け（app-links.js）。ログインの前に Google が読むので gate より先
    if (url.pathname === '/.well-known/assetlinks.json' && request.method === 'GET') return assetLinksResponse();
    const blocked = await gate(request, env, url);
    if (blocked) return blocked;
    // たぐりとは and ログイン are one page now; old links to /about still land there.
    if (url.pathname === '/about') return redirect('/login');
    if (url.pathname === '/login' && request.method === 'GET') return loginPage(request, env);
    if (url.pathname === '/oauth/calendar' && request.method === 'GET') return calendarCallbackPage(request, env);
    const poster = await posterFromR2(request, env, url);
    if (poster) return poster;
    // The Worker's own health (catalogue date, free-tier counters) even while the
    // Render bridge serves the other /api/ paths: catalog-age.yml and the crawler watch it.
    if (url.pathname === '/api/health' && request.method === 'GET') return json(await health(env.DB, env),200,{'Cache-Control':'public, max-age=300'});
    const migrationAPI=url.pathname.startsWith('/migration-api/');
    const native = await nativeRoute(request, env, url);
    if (native) return native;
    if(env.ORIGINAL_UI_BRIDGE==='true' && !migrationAPI && isOriginalRoute(url.pathname) && (!allNative(env) || stillBridged(url.pathname)))return originalUI(request);
    if(migrationAPI)url.pathname=url.pathname.replace('/migration-api/','/api/');
    // After the switch the menu has its own アカウント page (screens/account.js); the
    // older 「アカウント・記録」 page (/migration-data/) keeps only the passkey settings.
    if (!url.pathname.startsWith('/api/')) return withCard(withWorkerParts(await env.ASSETS.fetch(request)), url);
    try {
      const path = url.pathname; const method = request.method;
      if (method !== 'GET' && method !== 'POST') fail(405,'対応していない操作です。');
      if (method === 'POST' && request.headers.get('origin') !== url.origin) fail(403,'同じサイトから操作してください。');
      if (method === 'GET' && path === '/api/health') return json(await health(env.DB, env),200,{'Cache-Control':'public, max-age=300'});
      if (method === 'GET' && path === '/api/catalogue') {
        // Public catalogue only: never include an owner's ranking or private reasons.
        const rows = await env.DB.prepare('SELECT id,title,date,venue,url,metadata FROM catalogue WHERE date>=? ORDER BY date,id LIMIT 1000').bind(new Date(Date.now()-30*86400000).toISOString().slice(0,10)).all();
        const items=rows.results.map(({metadata,...c})=>{const m=JSON.parse(metadata);return {...c,group:m.group??'',fields:m.fields??{},synopsis:m.synopsis??'',words:m.words??[],end_date:m.end_date??c.date};});
        return json({items},200,{'Cache-Control':'public, max-age=300'});
      }
      if (method === 'POST' && ['/api/register','/api/recover'].includes(path)) {
        const input = await body(request);
        let uid; let recovery; let plan; let used;
        if (path === '/api/register') {
          if (env.ALLOW_REGISTRATION !== 'true') fail(503,'新規登録を一時停止しています。');
          requireAgreement(input, fail);
          plan = await checkNewAccount(env.DB, env, fail, undefined, request);
          recovery = token(); uid = crypto.randomUUID();
        } else {
          const code = string(input.code, 80, true).replaceAll('-', '').toLowerCase();
          if (!/^[a-f0-9]{64}$/.test(code)) fail(401,'復旧コードを確認してください。');
          used = await hash(code);
          uid = (await env.DB.prepare('SELECT id FROM users WHERE recovery_hash=?').bind(used).first())?.id;
          if (!uid) fail(401,'復旧コードを確認してください。');
        }
        const commands = [];
        if (recovery) commands.push(guardedUserInsert(env.DB, plan, ['id','recovery_hash','created_at','terms_version','terms_at'], [uid,await hash(recovery),now(),TERMS_VERSION,now()]),
          ...countNewAccount(env.DB, plan, uid));
        // この端末の古いセッションは消す（firebase・パスキーと同じ。共有の端末で前の人のセッションが残らない）
        // 復旧コードでのログインは、そのコードがまだ有効なときだけセッションになる（同時に作り直されたら入れない、#126）
        const session = await startSession(env.DB, uid, commands, sessionCookie(request), used ? ['recovery_hash=?', used] : null);
        if (recovery) await confirmNewAccount(env.DB, env, fail, uid, request);
        if (used && !(await env.DB.prepare('SELECT 1 AS ok FROM sessions WHERE hash=?').bind(await hash(session)).first())) fail(401,'復旧コードを確認してください。');
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
        // The OAuth client for 「Google カレンダーから取り込む」 (public, like the API key).
        return json({...config, calendarClientId: env.GOOGLE_CALENDAR_CLIENT_ID || ''},200,{'Cache-Control':'public, max-age=300'});
      }
      const uid = await user(request,env.DB);
      if (method === 'GET' && path === '/api/auth/passkeys') return await passkey.list(request, env, uid);
      if (method === 'POST' && path === '/api/auth/passkeys/delete') return await passkey.remove(request, env, uid);
      if (method === 'GET' && ['/api/state','/api/export'].includes(path)) return json(await state(env.DB,uid));
      if (method === 'GET' && path === '/api/recommend') return json(await recommendFor(env.DB, uid, env.CLOCK?.today ?? jstToday(), env.CLOCK?.now ?? Date.now()));
      if (method === 'GET' && path === '/api/stages') return json(await stagesFor(env.DB, url.searchParams));
      if (method === 'GET' && path === '/api/onboarding') return json(await onboardingFor(env.DB, uid));
      if (method !== 'POST') fail(404,'見つかりませんでした。');
      const input = await body(request);
      // Writes that change what is recommended drop the cached result (the stamp
      // alone misses two edits within the same second).
      if (!shrinkingPath(path, input) && !(await d1RoomLeft(env.DB, env))) fail(503, STORAGE_FULL);
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
      if (path === '/api/recovery/reissue') return await reissueRecovery(request, env, uid);
      if (path === '/api/logout/all') {
        // Sign out every device, e.g. after losing a phone. Firebase ID tokens from
        // sign-ins before this moment are refused from now on (tokens_valid_after, #127):
        // within their 5 minutes they could otherwise be exchanged for a new session.
        await env.DB.batch([env.DB.prepare('UPDATE users SET tokens_valid_after=? WHERE id=?').bind(now(),uid),
          env.DB.prepare('DELETE FROM sessions WHERE user_id=?').bind(uid)]);
        return json({ok:true},200,{'Set-Cookie':`${COOKIE}=; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=0`});
      }
      if (path === '/api/logout') {
        const raw = sessionCookie(request);
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
