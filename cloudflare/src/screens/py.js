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
