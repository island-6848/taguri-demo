// Person-score recommendations in the Worker (step 2 of moving them off
// Render). A port of score_from_index in scripts/build_recommend_index.py,
// itself checked against tools/review/user_recommender.py (person-feedback-v1).
// test/recommend.test.js runs this against Python's output on the same
// synthetic catalogue and must agree on stages, order, scores and reasons.
//
// Parity details:
// - Arithmetic is done in the same order and grouping as Python.
// - round(x, 6) == Number(x.toFixed(6)) for these values: both round the exact
//   binary value, and an exact decimal tie at the 7th digit cannot occur.
// - Strings compare by code point, as Python does (not UTF-16 units).

export const SMOOTH_A = 1, SMOOTH_B = 2, CONF_K = 3, TOP_N = 3;
const GRADES = new Set(['◎', '○', '△', '×']);
const KEYS_PER_QUERY = 49;     // D1 binds at most 100 parameters: ver + 2 per key
const IDS_PER_QUERY = 98;

// Fast path: k/1e6 is the double nearest to the decimal k·10^-6 (both exact
// integers, IEEE division), i.e. the same as Number(x.toFixed(6)), as long as
// x·1e6 is not within a hair of a .5 boundary; then fall back to toFixed.
const round6 = x => {
  const y = x * 1e6, f = y - Math.floor(y);
  return Math.abs(f - 0.5) < 1e-6 ? Number(x.toFixed(6)) : Math.round(y) / 1e6;
};
export function cmp(a, b) {
  a = String(a); b = String(b);
  if (a === b) return 0;
  let i = 0, j = 0;
  while (i < a.length && j < b.length) {
    const x = a.codePointAt(i), y = b.codePointAt(j);
    if (x !== y) return x < y ? -1 : 1;
    i += x > 0xffff ? 2 : 1; j += y > 0xffff ? 2 : 1;
  }
  return i >= a.length ? -1 : 1;     // the shorter one is a prefix of the other
}
const cmpTuple = (a, b) => { for (let i = 0; i < a.length; i++) { const c = typeof a[i] === 'number' ? (a[i] < b[i] ? -1 : a[i] > b[i] ? 1 : 0) : cmp(a[i], b[i]); if (c) return c; } return 0; };

/** One rating per linked stage (latest), unlinked records by their own key. */
export function independentRatings(rows) {
  const sorted = [...rows].sort((r, s) => cmpTuple([r.updated_at || r.date || '', r.key || ''], [s.updated_at || s.date || '', s.key || '']));
  const grouped = new Map();
  for (const row of sorted) {
    if (!GRADES.has(row.verdict)) continue;
    const key = row.stage_id ? 'stage\u0000' + row.stage_id : 'work\u0000' + row.key;
    grouped.set(key, row);         // like a Python dict: a later row keeps the key's first slot
  }
  return [...grouped.values()];
}

/** (role, person) -> [n, o]: records naming the person, and how many were ◎. */
export function buildRoster(rated) {
  const tally = new Map();
  for (const r of rated) {
    const pos = r.verdict === '◎' ? 1 : 0;
    for (const [role, person] of r.people || []) {
      const k = role + '\u0000' + person;
      const t = tally.get(k) || [0, 0];
      t[0] += 1; t[1] += pos;
      tally.set(k, t);
    }
  }
  return tally;
}

/**
 * Ranked upcoming stages with a positive person score, ordered like
 * user_recommender.finish before tour grouping.
 * postingsFor(keys [[role, person]...]) -> [[role, person, stage_id, role_w, group]...]
 * stagesFor(stageIds) -> Map(stage_id -> {start, end})
 */
export async function scoreFromIndex({postingsFor, stagesFor, rated, multipliers = {}, today}) {
  rated = independentRatings(rated);
  const base = rated.filter(r => r.verdict === '◎').length / Math.max(rated.length, 1);
  const roster = buildRoster(rated);
  // Per person: x = ◎ rate (smoothed) minus the user's overall ◎ rate, and the
  // confidence n/(n+3). A part's contribution is x times positive weights, so a
  // person with x <= 0 can never add to any stage: such people are not even
  // queried (fewer D1 rows and less CPU, same result as Python).
  const factor = new Map();
  for (const [k, [n, o]] of roster) {
    if (!n || !o) continue;
    const x = (o + SMOOTH_A) / (n + SMOOTH_B) - base;
    if (x > 0) factor.set(k, [x, n / (n + CONF_K), n]);
  }
  const keys = [...factor.keys()].map(k => k.split('\u0000')).sort((a, b) => cmpTuple(a, b));
  const byStage = new Map();
  const mult = g => (Object.prototype.hasOwnProperty.call(multipliers, g) ? multipliers[g] : 1.0);
  for (const [role, person, sid, roleW, group] of await postingsFor(keys)) {
    const [x, conf, n] = factor.get(role + '\u0000' + person);
    // Same operations and order as Python: contrib *= n/(n+3) * role_w * multiplier
    const contrib = x * (conf * roleW * mult(group));
    if (contrib > 0) {
      if (!byStage.has(sid)) byStage.set(sid, []);
      byStage.get(sid).push([round6(contrib), role, person, n, group]);
    }
  }
  const stages = await stagesFor([...byStage.keys()]);
  const out = [];
  for (const [sid, parts] of byStage) {
    const st = stages.get(sid);
    if (!st || (st.end && st.end < today)) continue;
    if (st.start && st.start <= today) continue;          // already running
    parts.sort((p, q) => (q[0] - p[0]) || cmp(p[1], q[1]) || cmp(p[2], q[2]));
    const b = round6(parts.slice(0, TOP_N).reduce((s, p) => s + p[0], 0));
    if (b <= 0) continue;
    const strong = parts.filter(p => p[1] === '出演' || p[3] >= 2).reduce((s, p) => s + mult(p[4]), 0);
    out.push({stage_id: sid, b, strong, parts: parts.map(p => p.slice(0, 4))});
  }
  out.sort((x, y) => (y.strong - x.strong) || (y.b - x.b) || cmp(x.stage_id, y.stage_id));
  return out;
}

/** The same contract over D1 (or SQLite in tests): the queries the Worker issues. */
export function d1Access(db, ver, counter = {rows: 0, queries: 0}) {
  return {
    counter,
    async postingsFor(keys) {
      const out = [];
      for (let i = 0; i < keys.length; i += KEYS_PER_QUERY) {
        const chunk = keys.slice(i, i + KEYS_PER_QUERY);
        const sql = 'SELECT role,person,stage_id,role_w,role_group FROM rec_credit WHERE ver=? AND (role,person) IN (VALUES '
          + chunk.map(() => '(?,?)').join(',') + ')';
        const {results} = await db.prepare(sql).bind(ver, ...chunk.flat()).all();
        counter.rows += results.length; counter.queries += 1;
        out.push(...results.map(r => [r.role, r.person, r.stage_id, r.role_w, r.role_group]));
      }
      return out;
    },
    async stagesFor(ids) {
      const map = new Map();
      for (let i = 0; i < ids.length; i += IDS_PER_QUERY) {
        const chunk = ids.slice(i, i + IDS_PER_QUERY);
        const {results} = await db.prepare('SELECT stage_id,start,end FROM rec_stage WHERE ver=? AND stage_id IN ('
          + chunk.map(() => '?').join(',') + ')').bind(ver, ...chunk).all();
        counter.rows += results.length; counter.queries += 1;
        for (const r of results) map.set(r.stage_id, {start: r.start, end: r.end});
      }
      return map;
    },
    async peopleFor(ids) {
      const map = new Map();
      for (let i = 0; i < ids.length; i += IDS_PER_QUERY) {
        const chunk = ids.slice(i, i + IDS_PER_QUERY);
        const {results} = await db.prepare('SELECT stage_id,people FROM rec_people WHERE ver=? AND stage_id IN ('
          + chunk.map(() => '?').join(',') + ')').bind(ver, ...chunk).all();
        counter.rows += results.length; counter.queries += 1;
        for (const r of results) map.set(r.stage_id, JSON.parse(r.people));
      }
      // Records linked to a past stage (past_stage, older than the index) bring its credits.
      const rest = ids.filter(s => !map.has(s));
      for (let i = 0; i < rest.length; i += IDS_PER_QUERY) {
        const chunk = rest.slice(i, i + IDS_PER_QUERY);
        let results = [];
        try {
          ({results} = await db.prepare('SELECT stage_id,people FROM past_stage WHERE stage_id IN ('
            + chunk.map(() => '?').join(',') + ')').bind(...chunk).all());
        } catch { break; }
        counter.rows += results.length; counter.queries += 1;
        for (const r of results) map.set(r.stage_id, JSON.parse(r.people));
      }
      return map;
    },
  };
}
