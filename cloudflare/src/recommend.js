// Person-score recommendations in the Worker (step 2 of moving them off
// Render). A port of score_from_index in scripts/build_recommend_index.py,
// itself checked against tools/review/user_recommender.py (person-ordinal-v3).
// test/recommend.test.js runs this against Python's output on the same
// synthetic catalogue and must agree on stages, order, scores and reasons.
//
// Parity details:
// - Arithmetic is done in the same order and grouping as Python.
// - round(x, 6) == Number(x.toFixed(6)) for these values: both round the exact
//   binary value, and an exact decimal tie at the 7th digit cannot occur.
// - Strings compare by code point, as Python does (not UTF-16 units).

export const CONF_K = 3, TOP_N = 3;
export const GRADE_VALUE = {'◎': 4, '○': 3, '△': 2, '×': 1};
export const MIN_LEVELS = 2, MAX_LEVELS = 11;
const SQRT12 = Math.sqrt(12);
// Favourites as pseudo ratings (user_recommender.SEED_Z / SEED_K and
// build_recommend_index.seeds_from_favourites).
export const SEED_Z = 0.4 * SQRT12, SEED_K = 3;
export const SEED_ROLES = ['出演', '演出', '脚本', '作', '原作', '翻訳', '潤色', '構成', '振付', '作曲', '音楽'];
export const SEED_KINDS = ['人', '原作者'], MAX_SEED_FAVS = 20, MAX_SEED_STAGES = 60;
// 詳細 (good / trouble per aspect): user_recommender.ASPECTS (checked against Python in the test).
export const ASPECTS = {
  story: ['話・脚本・構成', {'脚本': 1.0, '作': 1.0, '原作': 1.0, '原案': 1.0, '翻訳': 1.0, '潤色': 1.0, '構成': 1.0,
    '演出': 0.5, '演出・振付': 0.5, '#形式': 0.5, '#原作': 0.5, '#翻訳': 0.5}],
  direction: ['演出・見せ方', {'演出': 1.0, '演出・振付': 1.0, '美術': 0.5, '照明': 0.5, '音響': 0.5, '映像': 0.5, '#形式': 0.5}],
  acting: ['演技・出演', {'出演': 1.0, '演出': 0.2, '演出・振付': 0.2}],
  music: ['歌・音楽', {'作曲': 1.0, '音楽': 1.0, '編曲': 1.0, '音楽監督': 1.0, '歌唱指導': 1.0, '出演': 0.5, '#形式': 0.5}],
  dance: ['ダンス', {'振付': 1.0, '演出・振付': 1.0, '出演': 0.5}],
  design: ['美術・衣裳', {'美術': 1.0, '衣裳': 1.0, '衣装': 1.0, 'ヘアメイク': 1.0, 'メイク': 1.0, '小道具': 1.0, '演出': 0.5}],
  price: ['値段', {'#値段': 1.0}],
  venue: ['会場・座席', {'#会場': 1.0}],
};
/** user_recommender.parse_aspects: [troubles, goods] ("+code" = good), each in ASPECTS order. */
export function parseAspects(value) {
  const given = new Set(Array.isArray(value) ? value : String(value ?? '').split(','));
  const codes = Object.keys(ASPECTS);
  return [codes.filter(c => given.has(c)), codes.filter(c => given.has('+' + c))];
}
/** Canonical text of a record's aspects (troubles, then "+goods"), or null if invalid. */
export function cleanAspects(value) {
  const given = new Set((Array.isArray(value) ? value : String(value ?? '').split(',')).map(String).map(x => x.trim()).filter(Boolean));
  if ([...given].some(g => !Object.hasOwn(ASPECTS, g.replace(/^\+/, '')))) return null;
  const [troubles, goods] = parseAspects([...given]);
  if (troubles.some(c => goods.includes(c))) return null;
  return [...troubles, ...goods.map(c => '+' + c)].join(',');
}
function aspectShare(troubles, goods, role, positive) {
  const [main, other] = positive ? [goods, troubles] : [troubles, goods];
  const top = (codes, dflt) => { let m = -Infinity; for (const c of codes) { const v = Object.hasOwn(ASPECTS[c][1], role) ? ASPECTS[c][1][role] : 0.0; if (v > m) m = v; } return codes.length ? m : dflt; };
  return top(main, 1.0) * (1.0 - top(other, 0.0));
}

/** user_recommender.grade_of: [value, levels] of a saved rating ("◎" or "4/5"), or null. */
export function gradeOf(verdict) {
  if (Object.hasOwn(GRADE_VALUE, verdict)) return [GRADE_VALUE[verdict], 4];
  const m = /^(\d{1,2})\/(\d{1,2})$/.exec(String(verdict ?? ''));
  if (!m) return null;
  const value = Number(m[1]), levels = Number(m[2]);
  return levels >= MIN_LEVELS && levels <= MAX_LEVELS && value >= 1 && value <= levels ? [value, levels] : null;
}
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
    if (!gradeOf(row.verdict)) continue;
    const key = row.stage_id ? 'stage\u0000' + row.stage_id : 'work\u0000' + row.key;
    grouped.set(key, row);         // like a Python dict: a later row keeps the key's first slot
  }
  return [...grouped.values()];
}

/**
 * user_recommender.person_values: (role, person) -> [n, value], where value is
 * Σ z / (n + CONF_K) and z = (grade − the user's mean) / the user's spread
 * (◎○△× = 4/3/2/1). Same float operations in the same order as Python.
 */
export function personValues(rated, seeds = [], skip = new Set()) {
  // person-ordinal-v3: a rating's place among the user's own ratings on the
  // same scale, ((lower) + ½ (equal)) / n − ½, times √12.
  const byScale = new Map();
  for (const r of rated) {
    const [value, levels] = gradeOf(r.verdict);
    if (!byScale.has(levels)) byScale.set(levels, []);
    byScale.get(levels).push(value);
  }
  const tally = new Map();
  for (const r of rated) {
    const [value, levels] = gradeOf(r.verdict);
    const vals = byScale.get(levels);
    let below = 0, same = 0;
    for (const v of vals) { if (v < value) below += 1; else if (v === value) same += 1; }
    const z = ((below + 0.5 * same) / vals.length - 0.5) * SQRT12;
    const keys = [...new Set((r.people || []).map(([role, person]) => role + '\u0000' + person))].sort(cmp);
    // 詳細: a rating lands mainly on what was good (above the middle) or a
    // trouble (below it), less on what the other side points at.
    const [troubles, goods] = z ? parseAspects(r.aspects) : [[], []];
    const marked = troubles.length || goods.length;
    for (const k of keys) {
      const t = tally.get(k) || [0, 0, 0];
      t[0] += 1; t[1] += marked ? z * aspectShare(troubles, goods, k.slice(0, k.indexOf('\u0000')), z > 0) : z; t[2] += 1.0;
      tally.set(k, t);
    }
  }
  // Seeds: z = SEED_Z with weight w; they add to the weight, not to n.
  const w = SEED_K / (SEED_K + rated.length);
  for (const r of seeds) {
    const keys = [...new Set((r.people || []).filter(([, person]) => !skip.has(person)).map(([role, person]) => role + '\u0000' + person))].sort(cmp);
    for (const k of keys) {
      const t = tally.get(k) || [0, 0, 0];
      t[1] += w * SEED_Z; t[2] += w;
      tally.set(k, t);
    }
  }
  const values = new Map();
  for (const [k, [cnt, sum, wt]] of tally) values.set(k, [cnt, sum / (wt + CONF_K)]);
  return values;
}

/**
 * Ranked upcoming stages with a positive score, ordered like
 * user_recommender.finish before tour grouping (person-ordinal-v3).
 * postingsFor(keys [[role, person]...]) -> [[role, person, stage_id, role_w, group]...]
 * stagesFor(stageIds) -> Map(stage_id -> {start, end})
 */
export async function scoreFromIndex({postingsFor, stagesFor, rated, multipliers = {}, today, seeds = [], skip = new Set()}) {
  rated = independentRatings(rated);
  const values = personValues(rated, seeds, skip);
  const seeded = new Set(seeds.map(r => r.stage_id));
  // Everyone with a non-zero value can raise or lower a show.
  const keys = [...values.entries()].filter(([, [, v]]) => v).map(([k]) => k.split('\u0000')).sort((a, b) => cmpTuple(a, b));
  const byStage = new Map();
  const mult = g => (Object.prototype.hasOwnProperty.call(multipliers, g) ? multipliers[g] : 1.0);
  for (const [role, person, sid, roleW, group] of await postingsFor(keys)) {
    const [n, value] = values.get(role + '\u0000' + person);
    // Same operations and order as Python: value * (role_w * multiplier)
    const contrib = round6(value * (roleW * mult(group)));
    if (contrib) {
      if (!byStage.has(sid)) byStage.set(sid, []);
      byStage.get(sid).push([contrib, role, person, n, group]);
    }
  }
  const stages = await stagesFor([...byStage.keys()]);
  const out = [];
  for (const [sid, all] of byStage) {
    const st = stages.get(sid);
    if (seeded.has(sid) || !st || (st.end && st.end < today)) continue;
    if (st.start && st.start <= today) continue;          // already running
    // Kind-of-show tags ("#axis") add their mean; people add the strongest 3
    // up and 3 down (user_recommender.b_score).
    const people = all.filter(p => !p[1].startsWith('#'));
    const kinds = all.filter(p => p[1].startsWith('#')).sort((p, q) => cmp(p[1], q[1]) || cmp(p[2], q[2]));
    const parts = people.filter(p => p[0] > 0).sort((p, q) => (q[0] - p[0]) || cmp(p[1], q[1]) || cmp(p[2], q[2]));
    const negative = people.filter(p => p[0] < 0).sort((p, q) => (p[0] - q[0]) || cmp(p[1], q[1]) || cmp(p[2], q[2]));
    // Python: sum(positive top 3) + sum(negative top 3) + sum(kinds) / len, each sum from 0.
    let pos = 0, neg = 0, ks = 0;
    for (const p of parts.slice(0, TOP_N)) pos += p[0];
    for (const p of negative.slice(0, TOP_N)) neg += p[0];
    for (const p of kinds) ks += p[0];
    const b = round6(pos + neg + (kinds.length ? ks / kinds.length : 0));
    if (b <= 0) continue;
    out.push({stage_id: sid, b, strong: b, parts: parts.map(p => p.slice(0, 4))});
  }
  out.sort((x, y) => (y.strong - x.strong) || (y.b - x.b) || cmp(x.stage_id, y.stage_id));
  return out;
}

/**
 * build_recommend_index.seeds_from_favourites: candidate stages crediting a
 * favourite person / original author, with their people. Returns {seeds, skip}.
 */
export async function seedsFromFavourites({postingsFor, peopleFor}, favourites) {
  const names = [...new Set(favourites.filter(f => SEED_KINDS.includes(f.kind)).map(f => f.name))].sort(cmp).slice(0, MAX_SEED_FAVS);
  if (!names.length) return {seeds: [], skip: new Set()};
  const keys = names.flatMap(name => SEED_ROLES.map(role => [role, name])).sort(cmpTuple);
  const sids = [...new Set((await postingsFor(keys)).map(r => r[2]))].sort(cmp).slice(0, MAX_SEED_STAGES);
  const people = await peopleFor(sids);
  return {seeds: sids.filter(sid => people.get(sid)?.length).map(sid => ({stage_id: sid, people: people.get(sid)})), skip: new Set(names)};
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
      return map;
    },
  };
}
