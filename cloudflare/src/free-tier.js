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
