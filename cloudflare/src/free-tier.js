// Free-tier guards kept by the Worker (docs/free-tier-budget.md). The numbers
// for the crawler side live in scripts/free_tier.py (CAPS).
//
// R2 bills reads beyond the free 10 million Class B operations a month (起案者の指示
// 「必ず無料の範囲内にして。絶対超えないで」, docs/free-tier-budget.md). The Worker counts
// its reads in D1 (`usage`, migration 0014) and stops reading R2 at R2_READS_CAP:
// posters then come from the Render bridge as before. Counting every read would
// write a D1 row per image, so one read in R2_READ_SAMPLE adds R2_READ_SAMPLE;
// every isolate re-reads the total at least once a minute. The Cache API does
// nothing on *.workers.dev, so the browser cache (immutable, a week) is what
// keeps reads down. Any error counts as "over": R2 is never read unmetered.
export const R2_READS_CAP = 3_000_000;
const R2_READ_SAMPLE = 20;
export const r2Gate = {month: '', off: false, at: 0};
export async function r2ReadAllowed(env, nowMs = Date.now(), random = Math.random) {
  const month = new Date(nowMs).toISOString().slice(0, 7), key = `r2_get:${month}`;
  const sample = Number(env.R2_READ_SAMPLE) || R2_READ_SAMPLE;
  try {
    if (r2Gate.month !== month || nowMs - r2Gate.at > 60_000) {
      const n = (await env.DB.prepare('SELECT n FROM usage WHERE k=?').bind(key).first())?.n || 0;
      Object.assign(r2Gate, {month, at: nowMs, off: n >= R2_READS_CAP});
    }
    if (r2Gate.off) return false;
    if (random() * sample < 1) {
      const n = (await env.DB.prepare('INSERT INTO usage(k, n) VALUES (?, ?) ON CONFLICT(k) DO UPDATE SET n = n + excluded.n RETURNING n')
        .bind(key, sample).first())?.n || 0;
      if (n >= R2_READS_CAP) { r2Gate.off = true; return false; }
    }
    return true;
  } catch {
    Object.assign(r2Gate, {month, at: nowMs, off: true});
    return false;
  }
}

// D1 storage (起案者の指示 2026-10-14「数えてから決めて」, dec-account-cap-counted). The free
// plan has 5 GB; over it, writes fail. One user's rows are capped (triggers, 0001・0016・0021)
// but long texts make the worst case about 220 MB a user (measured, docs/free-tier-budget.md),
// so the Worker also watches the database's own size: D1 returns it with every query
// (meta.size_after). At D1_BYTES_CAP (80 % of 5 GB) every write that can grow storage
// and every sign-up is refused; reading and deleting keep working. The size is re-read at
// most once a minute per isolate (one row read). Unlike R2, D1 Free never bills (it stops
// at its limits), so a size that cannot be read lets the write through rather than take
// the service down.
export const D1_BYTES_CAP = 4_000_000_000;
// Accounts: one user who opens screens every day reads about 35,000 rows (300 records:
// ~500 rows a screen, 30 screens, plus the recommendation recomputed 2 times at ~10,000);
// 80 % of the 5 million rows a day is about 110 such users. With about a third of the
// accounts active on a day, 300 accounts stay within it (an estimate, not a measurement:
// q-d1-reads-real). New accounts per day keep a burst from spending the day's writes.
export const MAX_ACCOUNTS = 300;
export const NEW_ACCOUNTS_PER_DAY = 30;
export const d1Gate = {at: 0, bytes: null, full: false};
export async function d1Bytes(db, nowMs = Date.now()) {
  if (d1Gate.bytes !== null && nowMs - d1Gate.at < 60_000) return d1Gate.bytes;
  try {
    const r = await db.prepare('SELECT 1').all();
    const bytes = Number(r?.meta?.size_after);
    Object.assign(d1Gate, {at: nowMs, bytes: Number.isFinite(bytes) ? bytes : null});
  } catch {
    Object.assign(d1Gate, {at: nowMs, bytes: null});
  }
  return d1Gate.bytes;
}
/** False when the database is at D1_BYTES_CAP. Without a size (tests, local SQLite) it is allowed. */
export async function d1RoomLeft(db, env, nowMs = Date.now()) {
  const cap = Number(env?.D1_BYTES_CAP) || D1_BYTES_CAP;
  const bytes = await d1Bytes(db, nowMs);
  d1Gate.full = bytes !== null && bytes >= cap;
  return !d1Gate.full;
}

// 公演修正依頼（migration 0030, src/screens/fixrequest.js）。1 人 1 日の依頼の数と、起案者へのメールの 1 日の数。
// メールは起案者の Gmail から自分宛てに送る（Gmail の 1 日の送信の上限は 500 通。そのずっと手前で止める）。
// 上限を越えた日の依頼は保存だけして、管理画面で見る
export const FIX_REQUESTS_PER_USER_DAY = 5;
export const FIX_MAILS_PER_DAY = 30;
// 保存の上限（issue #129）。日をまたいで送り続けても行と本文が増え続けないようにする。
// 1 人の未対応 10 件・1 人の保存 50 件・全体 2,000 件。本文は 1,000 字（UTF-8 で 3 KB）までなので、
// 全体でも 2,000 × 約 3 KB ≈ 6 MB（D1 の上限 D1_BYTES_CAP の 0.2 % 足らず）。
// 対応済み（done / dropped）の本文は 30 日で消し、行は 180 日で消す（毎日の定期実行、src/screens/fixrequest.js）
export const FIX_OPEN_PER_USER = 10;
export const FIX_STORED_PER_USER = 50;
export const FIX_STORED_TOTAL = 2000;
export const FIX_RESOLVED_BODY_DAYS = 30;
export const FIX_RESOLVED_ROW_DAYS = 180;
