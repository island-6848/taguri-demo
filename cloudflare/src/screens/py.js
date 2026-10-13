// Small Python equivalents the screen ports need so their HTML is byte-for-byte
// what tools/taguri (Python) produces. Each is checked against Python in
// test/screens-py.test.js.

/** str(x) for the values the screens print (None, bools, ints, strings). */
export function pyStr(x) {
  if (x === null || x === undefined) return 'None';
  if (x === true) return 'True';
  if (x === false) return 'False';
  if (typeof x === 'number') {
    if (Number.isInteger(x)) return String(x);
    return pyFloat(x);
  }
  return String(x);
}

/** repr(float) — shortest round-trip, Python's exponent rules. */
export function pyFloat(x) {
  if (Number.isNaN(x)) return 'nan';
  if (!Number.isFinite(x)) return x > 0 ? 'inf' : '-inf';
  if (Number.isInteger(x) && Math.abs(x) < 1e16) return x.toFixed(1);
  const s = String(x);                       // JS: shortest round-trip digits too
  const m = s.match(/^(-?)(\d)(?:\.(\d+))?e([+-]\d+)$/);
  if (!m) return s;
  const exp = Number(m[4]);
  // Python switches to exponent form for exp < -4 or exp >= 16; JS for exp < -6 or >= 21.
  if (exp < -4 || exp >= 16) return `${m[1]}${m[2]}${m[3] ? '.' + m[3] : ''}e${exp < 0 ? '-' : '+'}${String(Math.abs(exp)).padStart(2, '0')}`;
  return s;
}

/** html.escape(str(s)) with quote=True. */
export function E(s) {
  return pyStr(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#x27;');
}

/** urllib.parse.quote(s, safe='/') on UTF-8. */
export function quote(s, safe = '/') {
  let out = '';
  for (const b of new TextEncoder().encode(pyStr(s))) {
    const c = String.fromCharCode(b);
    if (/[A-Za-z0-9_.~-]/.test(c) || safe.includes(c)) out += c;
    else out += '%' + b.toString(16).toUpperCase().padStart(2, '0');
  }
  return out;
}

/** json.dumps(x, ensure_ascii=False) with Python's default separators. */
export function dumps(x) {
  if (x === null || x === undefined) return 'null';
  if (x === true) return 'true';
  if (x === false) return 'false';
  if (typeof x === 'number') return Number.isInteger(x) ? String(x) : pyFloat(x);
  if (typeof x === 'string') return JSON.stringify(x).replace(/[  ]/g, c => c);
  if (Array.isArray(x)) return '[' + x.map(dumps).join(', ') + ']';
  return '{' + Object.entries(x).map(([k, v]) => JSON.stringify(k) + ': ' + dumps(v)).join(', ') + '}';
}

/** Code-point string order (Python's default for str). */
export function cmp(a, b) {
  a = String(a); b = String(b);
  if (a === b) return 0;
  const x = Array.from(a), y = Array.from(b);
  for (let i = 0; i < Math.min(x.length, y.length); i++) {
    const p = x[i].codePointAt(0), q = y[i].codePointAt(0);
    if (p !== q) return p < q ? -1 : 1;
  }
  return x.length < y.length ? -1 : 1;
}

/** Stable sort by a key function returning arrays/strings/numbers, Python tuple order. */
export function sortBy(rows, key, reverse = false) {
  const order = (a, b) => {
    if (Array.isArray(a)) {
      for (let i = 0; i < Math.min(a.length, b.length); i++) { const c = order(a[i], b[i]); if (c) return c; }
      return a.length - b.length;
    }
    if (typeof a === 'number' || typeof a === 'boolean') return (a > b) - (a < b);
    return cmp(a, b);
  };
  const keyed = rows.map((r, i) => [key(r), i, r]);
  // Python's reverse=True keeps equal items in their original order.
  keyed.sort((p, q) => (reverse ? order(q[0], p[0]) : order(p[0], q[0])) || (p[1] - q[1]));
  return keyed.map(k => k[2]);
}

/** Python's len() for str: code points. */
export const len = s => Array.from(String(s)).length;

/** datetime('now','localtime') as SQLite writes it, in Japan time. */
export function localNow(now = Date.now()) {
  return new Date(now + 9 * 3600e3).toISOString().replace('T', ' ').slice(0, 19);
}

/** ValueError raised by a POST handler: serve.py answers 400 {"error": str(e)}. */
export class ValueError extends Error {}

/** Python's str.isspace() / re's \s on str (the same set). */
export const WS = '\\t\\n\\x0b\\x0c\\r\\x1c-\\x1f \\x85\\xa0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000';
const stripRe = new RegExp(`^[${WS}]+|[${WS}]+$`, 'g');
/** str.strip() with no argument. */
export const strip = s => String(s).replace(stripRe, '');

/** s[a:b] counted in code points, as Python slices str. */
export const slice = (s, a, b) => Array.from(String(s)).slice(a, b).join('');

/** int() of a string of Unicode decimal digits (re's \d matches every Nd digit). */
export function digitsInt(s) {
  let n = 0;
  for (const ch of String(s)) {
    let cp = ch.codePointAt(0), start = cp;
    // Nd digits come in runs of whole 0..9 sets; the value is the offset in the run.
    while (/\p{Nd}/u.test(String.fromCodePoint(start - 1))) start--;
    n = n * 10 + (cp - start) % 10;
  }
  return n;
}

/** str.isdigit() for the strings the screens test (dates: only Nd digits get in). */
export const isdigit = s => /^\p{Nd}+$/u.test(String(s));

/** repr(str). */
export function strRepr(s) {
  s = String(s);
  const q = s.includes("'") && !s.includes('"') ? '"' : "'";
  let out = q;
  for (const ch of s) {
    const cp = ch.codePointAt(0);
    if (ch === q || ch === '\\') out += '\\' + ch;
    else if (ch === '\n') out += '\\n';
    else if (ch === '\r') out += '\\r';
    else if (ch === '\t') out += '\\t';
    else if (cp < 0x20 || cp === 0x7f) out += '\\x' + cp.toString(16).padStart(2, '0');
    // Not printable (str.isprintable): other/separator categories except the space.
    else if (ch !== ' ' && /[\p{Cc}\p{Cf}\p{Cs}\p{Co}\p{Cn}\p{Zl}\p{Zp}\p{Zs}]/u.test(ch)) {
      out += cp < 0x100 ? '\\x' + cp.toString(16).padStart(2, '0')
        : cp < 0x10000 ? '\\u' + cp.toString(16).padStart(4, '0') : '\\U' + cp.toString(16).padStart(8, '0');
    } else out += ch;
  }
  return out + q;
}

/** repr() of a JSON value (str() of lists and dicts prints their items with repr). */
export function pyRepr(x) {
  if (typeof x === 'string') return strRepr(x);
  if (Array.isArray(x)) return '[' + x.map(pyRepr).join(', ') + ']';
  if (x && typeof x === 'object') return '{' + Object.entries(x).map(([k, v]) => strRepr(k) + ': ' + pyRepr(v)).join(', ') + '}';
  return pyStr(x);
}

/** str(b.get(name) or "") for a value parsed from a JSON request body. */
export function field(b, name) {
  const v = b[name];
  if (!v || (Array.isArray(v) && !v.length) || (typeof v === 'object' && !Array.isArray(v) && !Object.keys(v).length)) return '';
  return typeof v === 'string' ? v : pyRepr(v);
}

/** parse_qs(query).get(name, [dflt])[0] — parse_qs drops blank values. */
export function qsFirst(params, name, dflt = '') {
  return params.getAll(name).find(v => v !== '') ?? dflt;
}
/** parse_qs(query).get(name, []) */
export const qsAll = (params, name) => params.getAll(name).filter(v => v !== '');

// Exact decimal expansion of a non-negative double (toFixed(100) is exact for
// the magnitudes the screens format), used to find exact ties.
const isTie = (x, d) => /^50*$/.test(x.toFixed(100).split('.')[1].slice(d));

/** format(x, f'.{d}f'): correctly rounded, ties to even like Python. */
export function fmtF(x, d) {
  if (x < 0) { const s = fmtF(-x, d); return /[1-9]/.test(s) ? '-' + s : s; }
  let s = x.toFixed(d);                       // ties round up here
  if (isTie(x, d)) {
    const down = x.toFixed(100).slice(0, x.toFixed(100).indexOf('.') + (d ? d + 1 : 0));
    if (Number(down.replace('.', '').slice(-1)) % 2 === 0) s = down;
  }
  return s;
}

/** round(x, d) for a non-negative float. */
export const pyRound = (x, d) => Number(fmtF(x, d));

/** difflib.SequenceMatcher(None, a, b).ratio() (autojunk on, as by default). */
export function seqRatio(a, b) {
  a = Array.from(a); b = Array.from(b);
  const b2j = new Map();
  b.forEach((ch, j) => { if (!b2j.has(ch)) b2j.set(ch, []); b2j.get(ch).push(j); });
  if (b.length >= 200) {
    const ntest = Math.floor(b.length / 100) + 1;
    for (const [ch, idx] of [...b2j]) if (idx.length > ntest) b2j.delete(ch);
  }
  const longest = (alo, ahi, blo, bhi) => {
    let besti = alo, bestj = blo, bestsize = 0, j2len = new Map();
    for (let i = alo; i < ahi; i++) {
      const next = new Map();
      for (const j of b2j.get(a[i]) || []) {
        if (j < blo) continue;
        if (j >= bhi) break;
        const k = (j2len.get(j - 1) || 0) + 1;
        next.set(j, k);
        if (k > bestsize) { besti = i - k + 1; bestj = j - k + 1; bestsize = k; }
      }
      j2len = next;
    }
    // No junk function: extend over equal elements (the "popular" ones dropped above).
    while (besti > alo && bestj > blo && a[besti - 1] === b[bestj - 1]) { besti--; bestj--; bestsize++; }
    while (besti + bestsize < ahi && bestj + bestsize < bhi && a[besti + bestsize] === b[bestj + bestsize]) bestsize++;
    return [besti, bestj, bestsize];
  };
  let matches = 0;
  const queue = [[0, a.length, 0, b.length]];
  while (queue.length) {
    const [alo, ahi, blo, bhi] = queue.pop();
    const [i, j, k] = longest(alo, ahi, blo, bhi);
    if (k) {
      matches += k;
      if (alo < i && blo < j) queue.push([alo, i, blo, j]);
      if (i + k < ahi && j + k < bhi) queue.push([i + k, ahi, j + k, bhi]);
    }
  }
  const t = a.length + b.length;
  return t ? 2 * matches / t : 1;
}
