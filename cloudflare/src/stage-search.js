// Finding a stage by title, to link a record to it (GET /migration-api/stages).
// A port of search_index in scripts/build_recommend_index.py; the index holds
// rate_performances.title_key of every title, and titleKey below must give the
// same key for the query. test/stage-search.test.js checks both against Python.
import {cmp} from './recommend.js';

export const SEARCH_LIMIT = 20;
const GRAMS_PER_QUERY = 98;      // D1 binds at most 100 parameters: ver + grams
const IDS_PER_QUERY = 98;

// rate_performances: _CROWN and _DROP. Python's "\s" and str.strip() mean
// str.isspace(): JS's \s plus U+001C-001F and U+0085, minus U+FEFF. Python's
// "." is any code point except "\n"; "u" makes {0,12} count code points.
const S = '\\t\\n\\v\\f\\r \\x1c-\\x1f\\x85\\xa0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000';
const STRIP = new RegExp(`^[${S}]+|[${S}]+$`, 'gu');
const CROWN = new RegExp(`^[〈<（(【\\[][^\\n]{0,12}?[〉>）)】\\]][${S}]*`, 'u');
const DROP = new RegExp(`[『』「」【】〈〉\\[\\]（）()・･,，.。${S}\\-−–—~〜/／:：!！?？'"“”’]`, 'gu');

/** rate_performances.title_key */
export function titleKey(title) {
  const n = String(title ?? '').normalize('NFKC').replace(STRIP, '');
  // Both lowercase a word-final Σ to ς (Unicode's Final_Sigma rule).
  return n.replace(CROWN, '').replace(DROP, '').toLowerCase();
}

const chars = s => Array.from(s);
export function bigrams(key) {
  const c = chars(key), set = new Set();
  for (let i = 0; i + 1 < c.length; i++) set.add(c[i] + c[i + 1]);
  return [...set].sort(cmp);
}

/** Stage ids best first; entriesFor(grams) -> Map(gram -> [[sid, tkey, start, end]...]) */
export async function searchIndex(entriesFor, q, date = '', limit = SEARCH_LIMIT) {
  const k = titleKey(q);
  if (chars(k).length < 2) return [];
  const grams = bigrams(k);
  const lists = await entriesFor(grams);
  if (grams.some(g => !lists.has(g))) return [];
  let pool = lists.get(grams[0]);
  for (const g of grams) if (lists.get(g).length < pool.length) pool = lists.get(g);
  const hits = [];
  for (const [sid, tkey, start, end] of pool) {
    if (!tkey.includes(k)) continue;
    const miss = date && start && start <= date && (!end || date <= end) ? 0 : 1;
    const score = tkey === k ? 0 : tkey.startsWith(k) ? 1 : 2;
    hits.push([miss, score, chars(tkey).length, sid]);
  }
  hits.sort((a, b) => (a[0] - b[0]) || (a[1] - b[1]) || (a[2] - b[2]) || cmp(a[3], b[3]));
  return hits.slice(0, Math.min(200, Math.max(1, limit))).map(h => h[3]);
}

export function d1Search(db, ver, counter = {rows: 0, queries: 0}) {
  return {
    counter,
    async entriesFor(grams) {
      const out = new Map();
      for (let i = 0; i < grams.length; i += GRAMS_PER_QUERY) {
        const chunk = grams.slice(i, i + GRAMS_PER_QUERY);
        const {results} = await db.prepare(`SELECT gram,entries FROM rec_gram WHERE ver=? AND gram IN (${chunk.map(() => '?').join(',')}) ORDER BY gram,part`)
          .bind(ver, ...chunk).all();
        counter.rows += results.length; counter.queries += 1;
        for (const r of results) {
          if (!out.has(r.gram)) out.set(r.gram, []);
          out.get(r.gram).push(...JSON.parse(r.entries));
        }
      }
      return out;
    },
    /** Display fields of stages, in the order of ids (unknown ids are left out). */
    async stages(ids) {
      const map = new Map();
      for (let i = 0; i < ids.length; i += IDS_PER_QUERY) {
        const chunk = ids.slice(i, i + IDS_PER_QUERY);
        const {results} = await db.prepare(`SELECT stage_id,title,grp,start,end,entry FROM rec_stage WHERE ver=? AND stage_id IN (${chunk.map(() => '?').join(',')})`)
          .bind(ver, ...chunk).all();
        counter.rows += results.length; counter.queries += 1;
        for (const r of results) map.set(r.stage_id, r);
      }
      return ids.filter(id => map.has(id)).map(id => {
        const r = map.get(id), entry = JSON.parse(r.entry || '{}');
        return {stage_id: id, title: r.title, group: r.grp, start: r.start, end: r.end,
          theater: entry.theater || '', pref: entry.pref || '', url: entry.url || ''};
      });
    },
  };
}

