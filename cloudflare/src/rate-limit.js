// Request limits (security S13・S15, q-rate-limiting). Two layers:
//
// 1. A brake per visitor, from Cloudflare's Rate Limiting binding (free on
//    Workers Free; no D1 reads or writes). It runs before anything else, so a
//    flood from one address stops before it costs D1 reads (the sign-in check
//    reads D1 on every request). The binding counts per Cloudflare location and
//    lets a little more through than the limit ("permissive, eventually
//    consistent"), so it is a brake, not an exact count. The key is the
//    visitor's address (CF-Connecting-IP, set by Cloudflare and not settable by
//    the client). Without the binding (tests, a missing setting) or when it
//    errors, requests pass: the limit protects the free tier, it must not take
//    the service down.
// 2. An exact cap for what grows storage: new accounts per day (JST), counted
//    from users.created_at, so no new data about visitors is kept.
// 3. New accounts per address per day (NEW_ACCOUNTS_PER_IP_DAY). Without it one
//    address could take the whole day's cap in a few minutes, and the total
//    cap (MAX_ACCOUNTS) in ten days (安全の点検 2026-10-17). Counted in `usage`
//    under a hash of the address and the day (not the address itself); the
//    rows of earlier days are deleted when a new one is written.
//
// Numbers: AUTH (sign-in, sign-up, recovery) 10 per minute per address is far
// above what a person does; ANY 120 per 10 seconds per address covers a screen
// with its posters (about 20 requests) several times over.
import {NEW_ACCOUNTS_PER_DAY, MAX_ACCOUNTS, d1RoomLeft} from './free-tier.js';
export {NEW_ACCOUNTS_PER_DAY};

const AUTH_PATHS = /^\/(api|migration-api)\/(register|recover|auth\/firebase|auth\/passkey\/(register|login)\/(options|verify))$/;

export const NEW_ACCOUNTS_PER_IP_DAY = 3;

export const limitKind = (method, path) => (method === 'POST' && AUTH_PATHS.test(path)) ? 'auth' : 'any';

const visitor = request => request.headers.get('cf-connecting-ip') || 'unknown';

async function allowed(binding, key) {
  if (!binding?.limit) return true;
  try { return (await binding.limit({key})).success !== false; }
  catch { return true; }
}

/** A 429 response when this visitor is over the limit, else null. */
export async function rateLimit(request, env, url) {
  const kind = limitKind(request.method, url.pathname), ip = visitor(request);
  const ok = await allowed(env.RL_ANY, `any:${ip}`) && (kind !== 'auth' || await allowed(env.RL_AUTH, `auth:${ip}`));
  if (ok) return null;
  const message = '操作が続いたので少し止めています。1分ほど待ってから試してください。';
  const headers = {'Retry-After': '60', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'};
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/migration-api/') || url.pathname.startsWith('/img/'))
    return Response.json({ok: false, error: message}, {status: 429, headers});
  return new Response(message, {status: 429, headers: {...headers, 'Content-Type': 'text/plain; charset=utf-8'}});
}

// 枠の確保は、利用者の行を足す書き込みそのものの中で確かめる（issue #124）。先に数えてから別の書き込みで足すと、
// 同時に来た要求が同じ残り枠を読んで、そろって通ってしまう。checkNewAccount は読むだけの下見（断る理由を
// 文で返すため）で、何も数えない。数えるのは guardedUserInsert・countNewAccount を入れた batch が通ったときだけ。
// D1 の batch は 1 つのトランザクションとして順に実行されるので、条件付きの INSERT が見る数は、ほかの登録と
// 食い違わない。パスキーの応答が署名の確認で断られたときも、枠は減らない（issue #125）。

const jstDayStart = nowSec => { const jst = 9 * 3600; return Math.floor((nowSec + jst) / 86400) * 86400 - jst; };

/**
 * 新規登録の下見。上限に達していれば fail（503・429）を投げ、通るなら確保に使う値（plan）を返す。
 * 読むだけで、枠は数えない。
 */
export async function checkNewAccount(db, env, fail, nowSec = Math.floor(Date.now() / 1000), request = null) {
  const most = Number(env.MAX_ACCOUNTS) || MAX_ACCOUNTS;
  const all = (await db.prepare('SELECT count(*) AS n FROM users').first())?.n || 0;
  if (all >= most) fail(503, 'いまは新規登録を受け付けていません（無料の範囲で動かすため、利用者の数に上限があります）。');
  if (!(await d1RoomLeft(db, env))) fail(503, 'いまは新規登録を受け付けていません（保存できる量の上限に近づいています）。');
  const cap = Number(env.NEW_ACCOUNTS_PER_DAY) || NEW_ACCOUNTS_PER_DAY;
  const dayStart = jstDayStart(nowSec);
  const n = (await db.prepare('SELECT count(*) AS n FROM users WHERE created_at>=?').bind(dayStart).first())?.n || 0;
  if (n >= cap) fail(503, '今日の新規登録の受付を締め切りました。明日もう一度お試しください。');
  const plan = {most, cap, dayStart, day: new Date((dayStart + 9 * 3600) * 1000).toISOString().slice(0, 10), key: null, per: 0};
  // 接続元が分からない要求（試験など）は数えない。本番では Cloudflare が必ず付ける
  if (request?.headers.get('cf-connecting-ip')) {
    plan.key = `newacct:${plan.day}:${await addressKey(request, plan.day)}`;
    plan.per = Number(env.NEW_ACCOUNTS_PER_IP_DAY) || NEW_ACCOUNTS_PER_IP_DAY;
    const seen = (await db.prepare('SELECT n FROM usage WHERE k=?').bind(plan.key).first())?.n || 0;
    if (seen >= plan.per) fail(429, SAME_PLACE);
  }
  return plan;
}
const SAME_PLACE = '同じ場所からの新規登録が続いています。明日もう一度お試しください。';

/**
 * 利用者の行を足す文。総数・その日の数・接続元の数が上限より少ないときだけ行が入る（入らなければ何も起きない）。
 * 同じ batch の後ろの文は、この行があるときだけ効くように書く（countNewAccount・startSession・パスキーの登録）。
 */
export function guardedUserInsert(db, plan, columns, values) {
  const conds = ['(SELECT count(*) FROM users)<?', '(SELECT count(*) FROM users WHERE created_at>=?)<?'];
  const args = [plan.most, plan.dayStart, plan.cap];
  if (plan.key) { conds.push('COALESCE((SELECT n FROM usage WHERE k=?),0)<?'); args.push(plan.key, plan.per); }
  return db.prepare(`INSERT INTO users(${columns.join(',')}) SELECT ${columns.map(() => '?').join(',')} WHERE ${conds.join(' AND ')}`)
    .bind(...values, ...args);
}

/** 接続元の数を 1 つ足す文（uid の行が同じ batch で入ったときだけ）。前の日の行は消す */
export function countNewAccount(db, plan, uid) {
  if (!plan.key) return [];
  return [db.prepare("DELETE FROM usage WHERE k LIKE 'newacct:%' AND k<?").bind(`newacct:${plan.day}`),
    db.prepare('INSERT INTO usage(k,n) SELECT ?,1 WHERE EXISTS (SELECT 1 FROM users WHERE id=?) ON CONFLICT(k) DO UPDATE SET n=n+1').bind(plan.key, uid)];
}

/** batch のあと: uid の行が入らなかった（ほかの登録が先に枠を使った）なら、理由を添えて fail を投げる */
export async function confirmNewAccount(db, env, fail, uid, request = null) {
  if (await db.prepare('SELECT 1 AS ok FROM users WHERE id=?').bind(uid).first()) return;
  await checkNewAccount(db, env, fail, undefined, request);
  fail(503, '新規登録が混み合っています。少し待ってからもう一度お試しください。');
}

/** 接続元の住所の代わり（日と住所のハッシュの先頭 12 バイト）。住所そのものは保存しない。接続元が分からなければ null */
export async function addressKey(request, day) {
  if (!request?.headers.get('cf-connecting-ip')) return null;
  const digest = new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(`${day}|${visitor(request)}`)));
  return [...digest.slice(0, 12)].map(b => b.toString(16).padStart(2, '0')).join('');
}
