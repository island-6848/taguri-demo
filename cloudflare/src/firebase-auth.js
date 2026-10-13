// Verify Firebase Authentication ID tokens without the Admin SDK.
//
// Follows Firebase's "verify ID tokens using a third-party JWT library" rules:
// RS256 only, kid must be one of Google's current securetoken keys, aud is the
// project ID, iss is https://securetoken.google.com/<project>, sub is the
// non-empty Firebase UID, exp in the future, iat and auth_time in the past.
// In addition this app requires a recent sign-in (auth_time) so an old token
// cannot be replayed to mint a new session, and accepts only the sign-in
// providers it offers: Google, and email link (reported as "password" with a
// verified address). Passwords are disabled in the Firebase console; an
// unverified "password" account is rejected here as a second guard.
//
// Only the UID leaves this module. The email address is never returned, so it
// cannot end up in D1 or in logs by accident.

export const JWKS_URL = 'https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com';
const MAX_TOKEN = 4096;
const SKEW = 60;                    // seconds of clock skew tolerated
export const MAX_AUTH_AGE = 300;    // sign-in must be at most 5 minutes old
const REFETCH_INTERVAL = 60;        // unknown kids refetch at most once a minute
const ALLOWED = new Set(['google.com', 'password']);

let cache = {keys: new Map(), expires: 0, fetched: 0};
export const resetKeyCache = () => { cache = {keys: new Map(), expires: 0, fetched: 0}; };

class AuthError extends Error {}
const reject = reason => { throw new AuthError(reason); };

function b64url(text) {
  if (!/^[A-Za-z0-9_-]*$/.test(text)) reject('encoding');
  const s = text.replaceAll('-', '+').replaceAll('_', '/');
  return Uint8Array.from(atob(s + '='.repeat((4 - s.length % 4) % 4)), c => c.charCodeAt(0));
}
const part = text => {
  try { return JSON.parse(new TextDecoder().decode(b64url(text))); } catch (e) { if (e instanceof AuthError) throw e; reject('json'); }
};

async function loadKeys(nowSec, force) {
  if (!force && cache.expires > nowSec) return;
  if (force && nowSec - cache.fetched < REFETCH_INTERVAL) return;
  cache.fetched = nowSec;
  const res = await fetch(JWKS_URL, {cf: {cacheTtl: 3600}});
  if (!res.ok) reject('jwks');
  const {keys} = await res.json();
  const map = new Map();
  for (const jwk of keys ?? []) {
    if (jwk.kty !== 'RSA' || !jwk.kid) continue;
    map.set(jwk.kid, await crypto.subtle.importKey('jwk', {kty: 'RSA', n: jwk.n, e: jwk.e, alg: 'RS256', ext: true},
      {name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256'}, false, ['verify']));
  }
  const maxAge = Number(res.headers.get('cache-control')?.match(/max-age=(\d+)/)?.[1] ?? 3600);
  cache = {keys: map, expires: nowSec + Math.min(maxAge, 6 * 3600), fetched: nowSec};
}

/** Returns {uid, provider} for a valid token, or throws. */
export async function verifyIdToken(idToken, projectId, nowSec = Math.floor(Date.now() / 1000)) {
  if (!projectId) throw Object.assign(new Error('firebase project not configured'), {config: true});
  if (typeof idToken !== 'string' || idToken.length > MAX_TOKEN) reject('size');
  const pieces = idToken.split('.');
  if (pieces.length !== 3) reject('shape');
  const [h, p, s] = pieces;
  const header = part(h), payload = part(p);
  if (header.alg !== 'RS256' || typeof header.kid !== 'string') reject('alg');
  await loadKeys(nowSec, false);
  if (!cache.keys.has(header.kid)) await loadKeys(nowSec, true);
  const key = cache.keys.get(header.kid);
  if (!key) reject('kid');
  const ok = await crypto.subtle.verify('RSASSA-PKCS1-v1_5', key, b64url(s), new TextEncoder().encode(`${h}.${p}`));
  if (!ok) reject('signature');
  const num = v => (typeof v === 'number' && Number.isFinite(v) ? v : reject('claims'));
  if (payload.aud !== projectId) reject('aud');
  if (payload.iss !== `https://securetoken.google.com/${projectId}`) reject('iss');
  if (typeof payload.sub !== 'string' || !payload.sub || payload.sub.length > 128) reject('sub');
  if (num(payload.exp) <= nowSec - SKEW) reject('exp');
  if (num(payload.iat) > nowSec + SKEW) reject('iat');
  const authTime = num(payload.auth_time);
  if (authTime > nowSec + SKEW || authTime < nowSec - MAX_AUTH_AGE) reject('auth_time');
  const provider = payload.firebase?.sign_in_provider;
  if (!ALLOWED.has(provider)) reject('provider');
  if (provider === 'password' && payload.email_verified !== true) reject('unverified');
  return {uid: payload.sub, provider};
}

export const isAuthError = e => e instanceof AuthError;
