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

// 回数制限が働いているかの様子（issue #133）。止まっても要求は通す（無料枠を守るための制限で、サービスを
// 止めるためのものではない）が、止まったことは分かるようにする:
// - /api/health の rate_limit に、結び付け（binding）があるか・この isolate で最近失敗したかを出す。
//   外の見張り（service-watch.yml の check_service.py）が 1 時間ごとに見て、無い・失敗中なら持ち主に知らせる
// - 失敗したときはログに 1 分に 1 行だけ出す（種類とエラーの名前だけ。接続元の住所や鍵は出さない）
// 数はこの isolate の中だけ（D1 には書かないので、使う量は増えない）。
// 認証口も同じく通す（障害時の方針、dec-rate-limit-fail-open）。復旧コードは 256 ビットの乱数、Firebase の
// トークンは署名を確かめ、パスキーは本人確認つきなので、制限が外れても当て推量では入れない。新規登録は D1 の
// 正確な上限（1 日・接続元ごと・全体）が別にあり、パスキーの未処理チャレンジも接続元ごとに数える
export const FAILING_MS = 10 * 60_000;          // 最後の失敗からこの間は failing と出す
const fresh = () => ({checked: 0, limited: 0, errors: 0, lastErrorAt: 0, loggedAt: 0, missingLogged: false});
export const rlStatus = {any: fresh(), auth: fresh()};
export function resetRateLimitStatus() { rlStatus.any = fresh(); rlStatus.auth = fresh(); }

async function allowed(binding, kind, key, nowMs = Date.now()) {
  const s = rlStatus[kind];
  if (!binding?.limit) {
    if (!s.missingLogged) { s.missingLogged = true; console.log(`rate limit ${kind}: no binding (requests pass unlimited)`); }
    return true;
  }
  try {
    const ok = (await binding.limit({key})).success !== false;
    s.checked++;
    if (!ok) s.limited++;
    return ok;
  } catch (e) {
    s.errors++; s.lastErrorAt = nowMs;
    if (nowMs - s.loggedAt >= 60_000) {
      s.loggedAt = nowMs;
      console.log(`rate limit ${kind}: binding failed (${String(e?.name || 'Error').slice(0, 40)}); requests pass unlimited`);
    }
    return true;
  }
}

/** /api/health の rate_limit。missing（結び付けが無い）・failing（最近失敗した）・ok のどれか。数だけで、住所は無い */
export function rateLimitHealth(env, nowMs = Date.now()) {
  const one = (kind, binding) => {
    const s = rlStatus[kind];
    const state = !binding?.limit ? 'missing' : (s.lastErrorAt && nowMs - s.lastErrorAt < FAILING_MS ? 'failing' : 'ok');
    return {state, checked: s.checked, limited: s.limited, errors: s.errors};
  };
  return {any: one('any', env?.RL_ANY), auth: one('auth', env?.RL_AUTH)};
}

/** A 429 response when this visitor is over the limit, else null. */
export async function rateLimit(request, env, url) {
  const kind = limitKind(request.method, url.pathname), ip = visitor(request);
  const ok = await allowed(env.RL_ANY, 'any', `any:${ip}`) && (kind !== 'auth' || await allowed(env.RL_AUTH, 'auth', `auth:${ip}`));
  if (ok) return null;
  const message = '操作が続いたので少し止めています。1分ほど待ってから試してください。';
  const headers = {'Retry-After': '60', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'};
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/migration-api/') || url.pathname.startsWith('/img/'))
    return Response.json({ok: false, error: message}, {status: 429, headers});
  return new Response(message, {status: 429, headers: {...headers, 'Content-Type': 'text/plain; charset=utf-8'}});
}

/**
 * Throws 503 when today's (JST) new accounts reached the cap, when there are
 * MAX_ACCOUNTS accounts, or when D1 is at its storage cap (free-tier.js).
 */
export async function checkNewAccount(db, env, fail, nowSec = Math.floor(Date.now() / 1000), request = null) {
  const most = Number(env.MAX_ACCOUNTS) || MAX_ACCOUNTS;
  const all = (await db.prepare('SELECT count(*) AS n FROM users').first())?.n || 0;
  if (all >= most) fail(503, 'いまは新規登録を受け付けていません（無料の範囲で動かすため、利用者の数に上限があります）。');
  if (!(await d1RoomLeft(db, env))) fail(503, 'いまは新規登録を受け付けていません（保存できる量の上限に近づいています）。');
  const cap = Number(env.NEW_ACCOUNTS_PER_DAY) || NEW_ACCOUNTS_PER_DAY;
  const jst = 9 * 3600, dayStart = Math.floor((nowSec + jst) / 86400) * 86400 - jst;
  const n = (await db.prepare('SELECT count(*) AS n FROM users WHERE created_at>=?').bind(dayStart).first())?.n || 0;
  if (n >= cap) fail(503, '今日の新規登録の受付を締め切りました。明日もう一度お試しください。');
  // 接続元が分からない要求（試験など）は数えない。本番では Cloudflare が必ず付ける
  if (request?.headers.get('cf-connecting-ip')) await countPerAddress(db, env, fail, request, dayStart);
}

/** 接続元の住所の代わり（日と住所のハッシュの先頭 12 バイト）。住所そのものは保存しない。接続元が分からなければ null */
export async function addressKey(request, day) {
  if (!request?.headers.get('cf-connecting-ip')) return null;
  const digest = new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(`${day}|${visitor(request)}`)));
  return [...digest.slice(0, 12)].map(b => b.toString(16).padStart(2, '0')).join('');
}

async function countPerAddress(db, env, fail, request, dayStart) {
  const day = new Date((dayStart + 9 * 3600) * 1000).toISOString().slice(0, 10);
  const key = `newacct:${day}:${await addressKey(request, day)}`;
  const per = Number(env.NEW_ACCOUNTS_PER_IP_DAY) || NEW_ACCOUNTS_PER_IP_DAY;
  const seen = (await db.prepare('SELECT n FROM usage WHERE k=?').bind(key).first())?.n || 0;
  if (seen >= per) fail(429, '同じ場所からの新規登録が続いています。明日もう一度お試しください。');
  await db.batch([
    db.prepare("DELETE FROM usage WHERE k LIKE 'newacct:%' AND k<?").bind(`newacct:${day}`),
    db.prepare('INSERT INTO usage(k,n) VALUES(?,1) ON CONFLICT(k) DO UPDATE SET n=n+1').bind(key)]);
}
