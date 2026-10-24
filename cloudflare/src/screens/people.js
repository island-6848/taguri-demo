// 記録を見返す ▸ 一緒に出てくる人のつながり: tools/taguri/people.py's panel(rated, owner=False)
// ported (with the rule-based 「この図から分かること」 reading; no LLM, no rebuild button). people.test.js checks
// panel() against people.panel on the same rated rows, byte for byte.
//
// **Floats follow Python step by step.** The force layout (layout/_separate) is written with the
// same operations in the same order as people.py: itertools.combinations order for the pairs,
// dict insertion order for the edges, `x or 0.01` for a zero distance. sum() in _text_w is
// CPython's compensated (Neumaier) sum, and widths come from unicodedata.east_asian_width (W/F).
import {E, fmtF, pyFloat, pyRound} from './py.js';
import {h2} from './icons.js';
import {anchor} from './anchor.js';
import {recDate} from './row.js';

const MAKER_ROLES = ['演出', '脚本', '作', '原作', '翻訳', '音楽', '作曲', '振付'];
const MAKER = new Set(MAKER_ROLES);
const KEEP = new Set(['出演', ...MAKER_ROLES]);
const MIN_WORKS = 2, LABEL_MIN = 4, LABEL_MAX = 16;
const W = 740.0, H = 620.0, PAD = 26.0;
const TAU = 2 * Math.PI;                       // == math.tau exactly
// charts.ROW_HREF / charts._table (local copies; charts._anchor is ./anchor.js)
const ROW_HREF = '/records/works?t=__TAGURI_TOKEN__';
function chTable(head, rows) {
  const th = head.map(h => `<th>${E(h)}</th>`).join('');
  const tr = rows.map(r => '<tr>' + r.map(c => `<td>${E(c)}</td>`).join('') + '</tr>').join('');
  return `<details class="tv"><summary>数字で見る</summary>`
    + `<table class="tbl mini"><thead><tr>${th}</tr></thead><tbody>${tr}</tbody></table></details>`;
}
/** f"{x:.{d}f}": toFixed rounds the exact value correctly, and only an exact tie (x·2·10^d an odd
 * integer ── then the float product is that integer too) needs fmtF's round-half-even. */
const fmt = (x, d) => (x >= 0 && x < 1e21 && !Number.isInteger(x * 2 * 10 ** d) ? x.toFixed(d) : fmtF(x, d));
const f1 = x => fmt(x, 1);

/** Python str order (code points) on UTF-16 strings, without splitting them into arrays. */
function cmp(a, b) {
  if (a === b) return 0;
  const n = Math.min(a.length, b.length);
  for (let i = 0; i < n; i++) {
    let x = a.charCodeAt(i), y = b.charCodeAt(i);
    if (x === y) continue;
    // Surrogates (D800–DFFF) stand for code points above FFFF: move them past E000–FFFF.
    if (x >= 0xD800) x += x >= 0xE000 ? -0x800 : 0x2000;
    if (y >= 0xD800) y += y >= 0xE000 ? -0x800 : 0x2000;
    return x < y ? -1 : 1;
  }
  return a.length < b.length ? -1 : 1;
}

// unicodedata.east_asian_width(c) in "WF" (Unicode 15.1.0, Python 3.13's unicodedata).
// test/people.test.js checks this table against the Python that made the fixture.
export const WF = [
  0x1100, 0x115F, 0x231A, 0x231B, 0x2329, 0x232A, 0x23E9, 0x23EC, 0x23F0, 0x23F0, 0x23F3, 0x23F3,
  0x25FD, 0x25FE, 0x2614, 0x2615, 0x2648, 0x2653, 0x267F, 0x267F, 0x2693, 0x2693, 0x26A1, 0x26A1,
  0x26AA, 0x26AB, 0x26BD, 0x26BE, 0x26C4, 0x26C5, 0x26CE, 0x26CE, 0x26D4, 0x26D4, 0x26EA, 0x26EA,
  0x26F2, 0x26F3, 0x26F5, 0x26F5, 0x26FA, 0x26FA, 0x26FD, 0x26FD, 0x2705, 0x2705, 0x270A, 0x270B,
  0x2728, 0x2728, 0x274C, 0x274C, 0x274E, 0x274E, 0x2753, 0x2755, 0x2757, 0x2757, 0x2795, 0x2797,
  0x27B0, 0x27B0, 0x27BF, 0x27BF, 0x2B1B, 0x2B1C, 0x2B50, 0x2B50, 0x2B55, 0x2B55, 0x2E80, 0x2E99,
  0x2E9B, 0x2EF3, 0x2F00, 0x2FD5, 0x2FF0, 0x303E, 0x3041, 0x3096, 0x3099, 0x30FF, 0x3105, 0x312F,
  0x3131, 0x318E, 0x3190, 0x31E3, 0x31EF, 0x321E, 0x3220, 0x3247, 0x3250, 0x4DBF, 0x4E00, 0xA48C,
  0xA490, 0xA4C6, 0xA960, 0xA97C, 0xAC00, 0xD7A3, 0xF900, 0xFAFF, 0xFE10, 0xFE19, 0xFE30, 0xFE52,
  0xFE54, 0xFE66, 0xFE68, 0xFE6B, 0xFF01, 0xFF60, 0xFFE0, 0xFFE6, 0x16FE0, 0x16FE4, 0x16FF0, 0x16FF1,
  0x17000, 0x187F7, 0x18800, 0x18CD5, 0x18D00, 0x18D08, 0x1AFF0, 0x1AFF3, 0x1AFF5, 0x1AFFB, 0x1AFFD,
  0x1AFFE, 0x1B000, 0x1B122, 0x1B132, 0x1B132, 0x1B150, 0x1B152, 0x1B155, 0x1B155, 0x1B164, 0x1B167,
  0x1B170, 0x1B2FB, 0x1F004, 0x1F004, 0x1F0CF, 0x1F0CF, 0x1F18E, 0x1F18E, 0x1F191, 0x1F19A, 0x1F200,
  0x1F202, 0x1F210, 0x1F23B, 0x1F240, 0x1F248, 0x1F250, 0x1F251, 0x1F260, 0x1F265, 0x1F300, 0x1F320,
  0x1F32D, 0x1F335, 0x1F337, 0x1F37C, 0x1F37E, 0x1F393, 0x1F3A0, 0x1F3CA, 0x1F3CF, 0x1F3D3, 0x1F3E0,
  0x1F3F0, 0x1F3F4, 0x1F3F4, 0x1F3F8, 0x1F43E, 0x1F440, 0x1F440, 0x1F442, 0x1F4FC, 0x1F4FF, 0x1F53D,
  0x1F54B, 0x1F54E, 0x1F550, 0x1F567, 0x1F57A, 0x1F57A, 0x1F595, 0x1F596, 0x1F5A4, 0x1F5A4, 0x1F5FB,
  0x1F64F, 0x1F680, 0x1F6C5, 0x1F6CC, 0x1F6CC, 0x1F6D0, 0x1F6D2, 0x1F6D5, 0x1F6D7, 0x1F6DC, 0x1F6DF,
  0x1F6EB, 0x1F6EC, 0x1F6F4, 0x1F6FC, 0x1F7E0, 0x1F7EB, 0x1F7F0, 0x1F7F0, 0x1F90C, 0x1F93A, 0x1F93C,
  0x1F945, 0x1F947, 0x1F9FF, 0x1FA70, 0x1FA7C, 0x1FA80, 0x1FA88, 0x1FA90, 0x1FABD, 0x1FABF, 0x1FAC5,
  0x1FACE, 0x1FADB, 0x1FAE0, 0x1FAE8, 0x1FAF0, 0x1FAF8, 0x20000, 0x2FFFD, 0x30000, 0x3FFFD
];
function wide(cp) {
  let lo = 0, hi = WF.length / 2 - 1;
  while (lo <= hi) {
    const m = (lo + hi) >> 1;
    if (cp < WF[2 * m]) hi = m - 1;
    else if (cp > WF[2 * m + 1]) lo = m + 1;
    else return true;
  }
  return false;
}

/** sum(xs) of floats as CPython 3.12+ adds them (Neumaier compensation; start is int 0). */
function pySum(xs) {
  if (!xs.length) return 0;
  let f = xs[0], c = 0;
  for (let i = 1; i < xs.length; i++) {
    const x = xs[i], t = f + x;
    c += Math.abs(f) >= Math.abs(x) ? (f - t) + x : (x - t) + f;
    f = t;
  }
  if (c && Number.isFinite(c)) f += c;
  return f;
}

/** people._text_w */
export function textW(s, fs = 11.5) {
  const xs = [];
  for (const ch of String(s)) xs.push(wide(ch.codePointAt(0)) ? fs : fs * 0.52);
  return pySum(xs);
}

// ---- math.cos / math.sin as CPython gives them.
// V8's Math.cos/sin (fdlibm) differ from CPython's (glibc) by 1 ulp for ~3% of the starting
// circle positions τ·i/n, and the 460 force iterations blow that ulp up into a different picture
// (checked: with Python's sin/cos values fed in, every byte matches). So sinCos() computes the
// correctly rounded value in double-double (≈106 bits), and circle() applies the few places where
// glibc rounds the other way (GLIBC_FIX below).
const twoSum = (a, b) => { const s = a + b, bb = s - a; return [s, (a - (s - bb)) + (b - bb)]; };
const quick = (a, b) => { const s = a + b; return [s, b - (s - a)]; };
const split = a => { const c = 134217729 * a, hi = c - (c - a); return [hi, a - hi]; };
function twoProd(a, b) {
  const p = a * b, [ah, al] = split(a), [bh, bl] = split(b);
  return [p, ((ah * bh - p) + ah * bl + al * bh) + al * bl];
}
function ddAdd(a, b) {
  let [s, e] = twoSum(a[0], b[0]);
  const [t, f] = twoSum(a[1], b[1]);
  e += t; [s, e] = quick(s, e); e += f;
  return quick(s, e);
}
function ddMul(a, b) {
  const [p, e] = twoProd(a[0], b[0]);
  return quick(p, e + (a[0] * b[1] + a[1] * b[0]));
}
function ddDivD(a, d) {
  const q1 = a[0] / d, [p, e] = twoProd(q1, d);
  const [s, e2] = twoSum(a[0], -p);
  return quick(q1, (s + (e2 - e + a[1])) / d);
}
const PIO2 = [1.5707963267948966, 6.123233995736766e-17, -1.4973849048591698e-33];
/** [math.sin(a), math.cos(a)] for 0 <= a <= 2π. */
export function sinCos(a) {
  if (a === 0) return [0, 1];
  const k = Math.round(a / PIO2[0]);
  const [h, l] = twoProd(k, PIO2[0]);
  const [s, e] = twoSum(a, -h);
  let r = twoSum(s, e - l);
  const [h2, l2] = twoProd(k, PIO2[1]);
  r = ddAdd(r, [-h2, -l2]);
  r = ddAdd(r, [-k * PIO2[2], 0]);
  const x2 = ddMul(r, r);
  let S = r, ts = r, C = [1, 0], tc = [1, 0];
  for (let n = 1; n < 40; n++) {
    ts = ddDivD(ddDivD(ddMul(ts, x2), 2 * n), 2 * n + 1);
    tc = ddDivD(ddDivD(ddMul(tc, x2), 2 * n - 1), 2 * n);
    const sg = n % 2 ? -1 : 1;
    S = ddAdd(S, [sg * ts[0], sg * ts[1]]);
    C = ddAdd(C, [sg * tc[0], sg * tc[1]]);
    if (Math.abs(ts[0]) <= Math.abs(S[0]) * 1e-34 && Math.abs(tc[0]) <= 1e-34) break;
  }
  const sn = S[0], cs = C[0];
  switch (((k % 4) + 4) % 4) {
    case 0: return [sn, cs];
    case 1: return [cs, -sn];
    case 2: return [-sn, -cs];
    default: return [-cs, sn];
  }
}

// **CPython's math.sin/cos are glibc's, and glibc is not correctly rounded everywhere.** For the
// angles τ·i/n with n < 512 (the core sizes this screen can meet), these are the places where
// glibc 2.39 (x86-64, FMA path) gives a neighbour of the correctly rounded value: n, i, Δsin, Δcos
// in ulps. test/people.test.js checks every τ·i/n with n < 512 against the fixture's Python
// and prints a new table when they drift apart (another libm / glibc).
export const TRIG_N = 512;
export const GLIBC_FIX = [
  19,11,1,0, 27,13,1,0, 38,22,1,0, 39,1,1,0, 40,33,1,0, 40,39,1,0, 41,22,1,0, 51,8,-1,0, 52,13,0,-1,
  54,26,1,0, 61,19,0,1, 76,44,1,0, 78,2,1,0, 78,47,0,-1, 80,66,1,0, 80,78,1,0, 82,44,1,0, 91,38,0,1,
  101,99,1,0, 102,16,-1,0, 103,3,1,0, 104,26,0,-1, 108,52,1,0, 114,11,1,0, 116,69,0,1, 117,3,1,0,
  120,99,1,0, 120,117,1,0, 122,38,0,1, 122,43,0,1, 133,74,-1,0, 140,47,0,-1, 144,97,0,-1, 147,33,-1,0,
  147,137,-1,0, 151,42,0,-1, 152,88,1,0, 153,24,-1,0, 154,25,1,0, 156,4,1,0, 156,94,0,-1,
  158,133,0,-1, 159,155,1,0, 160,132,1,0, 160,156,1,0, 163,66,-1,0, 164,88,1,0, 172,39,0,1,
  178,171,-1,0, 181,142,0,1, 182,76,0,1, 183,57,0,1, 183,156,1,0, 188,47,0,-1, 193,41,0,1, 195,5,1,0,
  196,5,1,0, 197,5,1,0, 200,195,1,0, 202,198,1,0, 204,32,-1,0, 206,6,1,0, 206,47,0,-1, 208,52,0,-1,
  210,31,0,-1, 211,118,1,0, 212,95,-1,0, 216,104,1,0, 224,99,-1,0, 228,22,1,0, 231,80,-1,0,
  231,82,0,1, 231,218,1,0, 232,49,0,-1, 232,138,0,1, 233,187,1,0, 234,6,1,0, 235,139,1,0, 237,157,0,1,
  239,81,-1,0, 240,198,1,0, 240,234,1,0, 242,79,0,-1, 242,137,0,-1, 242,201,-1,0, 243,50,0,-1,
  243,80,0,-1, 244,76,0,1, 244,86,0,1, 245,68,0,1, 255,40,-1,0, 255,199,0,1, 257,241,-1,0,
  261,167,-1,0, 262,79,1,0, 262,93,-1,0, 264,71,0,1, 264,229,0,1, 266,148,-1,0, 271,10,-1,0,
  271,128,-1,0, 273,7,1,0, 273,114,0,1, 277,222,0,-1, 278,189,-1,0, 278,237,-1,0, 279,79,0,1,
  279,121,1,0, 279,163,-1,0, 280,94,0,-1, 280,231,1,0, 280,273,1,0, 285,165,1,0, 287,88,0,1,
  287,220,0,1, 288,194,0,-1, 289,8,0,1, 294,66,-1,0, 294,274,-1,0, 302,84,0,-1, 303,297,1,0,
  304,176,1,0, 305,21,1,0, 305,260,1,0, 305,301,0,-1, 306,48,-1,0, 307,258,0,1, 307,298,-1,0,
  308,50,1,0, 308,237,0,1, 309,9,1,0, 309,303,-1,0, 311,172,1,0, 312,8,1,0, 312,188,0,-1, 313,199,1,0,
  314,189,-1,0, 316,266,0,-1, 317,301,1,0, 318,137,1,0, 318,310,1,0, 320,191,0,1, 320,264,1,0,
  320,312,1,0, 321,29,1,0, 321,193,-1,0, 323,116,-1,0, 325,153,1,0, 326,132,-1,0, 327,223,-1,0,
  328,176,1,0, 329,303,-1,0, 331,38,0,-1, 331,51,1,0, 331,306,-1,0, 332,83,0,-1, 332,175,-1,0,
  337,271,0,1, 337,309,-1,0, 339,206,0,-1, 339,271,0,1, 341,38,-1,0, 342,33,1,0, 343,46,0,1,
  343,77,-1,0, 344,78,0,1, 345,59,0,-1, 345,104,0,1, 349,37,0,-1, 350,59,0,-1, 351,9,1,0, 352,73,0,-1,
  353,77,0,1, 353,164,1,0, 354,17,1,0, 354,245,0,1, 354,253,0,-1, 356,342,-1,0, 357,56,-1,0,
  357,165,-1,0, 358,115,0,1, 359,3,1,0, 359,241,0,-1, 360,297,1,0, 360,351,1,0, 361,278,0,-1,
  362,284,0,1, 364,152,0,1, 366,114,0,1, 366,129,0,1, 366,199,0,1, 366,312,1,0, 368,197,-1,0,
  369,312,0,1, 373,298,0,-1, 375,154,0,1, 376,25,-1,0, 376,94,0,-1, 377,177,-1,0, 379,112,-1,0,
  380,37,0,-1, 380,273,0,1, 380,297,0,-1, 381,124,0,1, 381,272,0,-1, 383,176,-1,0, 385,302,0,-1,
  386,82,0,1, 387,76,0,1, 390,10,1,0, 390,235,0,-1, 391,118,0,1, 392,10,1,0, 392,149,-1,0,
  393,266,0,-1, 394,10,1,0, 394,291,0,-1, 395,15,1,0, 396,99,0,-1, 397,178,0,1, 397,330,0,1,
  397,333,0,-1, 397,346,0,-1, 399,222,-1,0, 399,278,0,-1, 400,390,1,0, 401,117,0,-1, 401,129,-1,0,
  401,288,0,-1, 404,137,0,-1, 404,231,0,-1, 404,396,1,0, 405,87,0,-1, 405,118,0,-1, 406,239,-1,0,
  407,136,0,-1, 407,188,1,0, 408,64,-1,0, 409,218,-1,0, 409,225,0,-1, 411,58,0,-1, 412,12,1,0,
  412,94,0,-1, 412,137,0,-1, 416,104,0,-1, 417,175,1,0, 420,62,0,-1, 420,141,0,-1, 422,89,0,-1,
  422,236,1,0, 423,205,1,0, 424,119,0,1, 424,190,-1,0, 424,397,-1,0, 425,239,0,1, 427,133,0,1,
  428,349,1,0, 429,11,1,0, 429,226,-1,0, 432,97,0,-1, 432,208,1,0, 432,291,0,-1, 433,381,0,-1,
  434,167,-1,0, 438,125,0,1, 440,429,1,0, 441,400,0,1, 441,411,-1,0, 442,317,0,1, 443,354,0,1,
  443,360,0,-1, 443,391,0,1, 448,198,-1,0, 449,98,0,-1, 449,197,0,1, 451,91,0,1, 451,368,1,0,
  453,126,0,-1, 454,19,-1,0, 455,190,0,1, 455,242,1,0, 456,44,1,0, 457,275,-1,0, 459,72,-1,0,
  459,183,0,-1, 459,428,-1,0, 462,160,-1,0, 462,164,0,1, 462,436,1,0, 464,73,0,-1, 464,98,0,-1,
  464,276,0,1, 464,429,-1,0, 466,147,0,-1, 466,195,0,1, 466,374,1,0, 467,450,1,0, 468,12,1,0,
  469,102,0,-1, 470,278,1,0, 471,101,0,-1, 471,193,1,0, 474,314,0,1, 474,399,0,-1, 476,107,0,-1,
  477,465,1,0, 478,162,-1,0, 479,433,-1,0, 480,396,1,0, 480,468,1,0, 481,339,0,-1, 484,131,0,1,
  484,158,0,-1, 484,274,0,-1, 484,402,-1,0, 484,421,1,0, 485,172,-1,0, 486,100,0,-1, 486,160,0,-1,
  487,230,1,0, 488,152,0,1, 488,172,0,1, 489,198,-1,0, 490,136,0,1, 490,171,0,1, 490,221,1,0,
  490,341,0,-1, 491,18,-1,0, 491,385,0,1, 493,94,0,-1, 494,31,-1,0, 497,43,0,-1, 499,145,0,1,
  500,413,0,1, 501,290,-1,0, 502,321,1,0, 502,365,0,-1, 504,451,1,0, 505,396,0,-1, 505,495,1,0,
  507,267,-1,0, 507,359,0,1, 507,467,1,0, 508,241,-1,0, 509,491,-1,0, 510,80,-1,0, 510,398,0,1,
  511,53,0,1, 511,496,0,-1
];
let fixMap = null;
const bitsOf = new DataView(new ArrayBuffer(8));
function ulps(x, d) {
  if (!d) return x;
  bitsOf.setFloat64(0, x);
  bitsOf.setBigInt64(0, bitsOf.getBigInt64(0) + BigInt(d));
  return bitsOf.getFloat64(0);
}
/** [math.sin(math.tau * i / n), math.cos(math.tau * i / n)] as the fixture's CPython gives them. */
export function circle(i, n) {
  const [sn, cs] = sinCos(TAU * i / n);
  if (n >= TRIG_N) return [sn, cs];
  if (!fixMap) {
    fixMap = new Map();
    for (let j = 0; j < GLIBC_FIX.length; j += 4) fixMap.set(GLIBC_FIX[j] * TRIG_N + GLIBC_FIX[j + 1], [GLIBC_FIX[j + 2], GLIBC_FIX[j + 3]]);
  }
  const f = fixMap.get(n * TRIG_N + i);
  return f ? [ulps(sn, f[0]), ulps(cs, f[1])] : [sn, cs];
}

/** people.build */
export function build(rated) {
  const perWork = new Map(), roles = new Map(), cnt = new Map(), titles = new Map();
  for (const r of rated) {
    const ps = new Set();
    for (const [role, person] of r.people || []) {
      if (!KEEP.has(role)) continue;
      ps.add(person);
      if (!roles.has(person)) roles.set(person, new Set());
      roles.get(person).add(role);
    }
    if (ps.size) {
      perWork.set(r.key, ps);
      for (const p of ps) {
        cnt.set(p, (cnt.get(p) || 0) + 1);
        if (!titles.has(p)) titles.set(p, []);
        titles.get(p).push([r.title || '', r.key]);
      }
    }
  }
  const nodes = [...cnt].filter(([, n]) => n >= MIN_WORKS).map(([p]) => p).sort(cmp);
  const nodeSet = new Set(nodes);
  const edges = new Map();                     // "a\0b" -> [a, b, weight], Counter insertion order
  const adj = new Map(nodes.map(p => [p, new Set()]));
  for (const ps of perWork.values()) {
    const s = [...ps].filter(p => nodeSet.has(p)).sort(cmp);
    for (let i = 0; i < s.length; i++) {
      for (let j = i + 1; j < s.length; j++) {
        const a = s[i], b = s[j], key = a + '\0' + b;
        const e = edges.get(key);
        if (e) e[2]++; else edges.set(key, [a, b, 1]);
        adj.get(a).add(b);
        adj.get(b).add(a);
      }
    }
  }
  const core = nodes.filter(p => adj.get(p).size);
  return {nodes, core, isolated: nodes.filter(p => !adj.get(p).size), edges, adj, cnt, roles, titles,
          n_works: perWork.size, n_rated: rated.length, n_people: cnt.size, cuts: cuts(core, adj)};
}

/** people._cuts: the people whose removal splits the network (articulation points).
 * Python removes each person in turn and counts the groups (O(V·(V+E))); the set is the same as
 * Tarjan's articulation points, found here in one depth-first pass (timeline() calls build() once
 * per dated record, so this is most of the screen's CPU). */
function cuts(nodes, adj) {
  const disc = new Map(), low = new Map(), art = new Set();
  let time = 0;
  for (const root of nodes) {
    if (disc.has(root)) continue;
    disc.set(root, time); low.set(root, time); time++;
    let rootKids = 0;
    // iterative DFS: [vertex, parent, iterator over neighbours]
    const st = [[root, null, adj.get(root)[Symbol.iterator]()]];
    while (st.length) {
      const top = st[st.length - 1], [v, parent, it] = top;
      const nx = it.next();
      if (!nx.done) {
        const q = nx.value;
        if (q === parent) continue;
        if (disc.has(q)) { if (disc.get(q) < low.get(v)) low.set(v, disc.get(q)); continue; }
        disc.set(q, time); low.set(q, time); time++;
        if (v === root) rootKids++;
        st.push([q, v, adj.get(q)[Symbol.iterator]()]);
        continue;
      }
      st.pop();
      if (parent !== null) {
        if (low.get(v) < low.get(parent)) low.set(parent, low.get(v));
        if (parent !== root && low.get(v) >= disc.get(parent)) art.add(parent);
      }
    }
    if (rootKids > 1) art.add(root);
  }
  return nodes.filter(p => art.has(p));
}

/** people.components */
export function components(g, skip = []) {
  const seen = new Set(skip), out = [];
  for (const p of g.core) {
    if (seen.has(p)) continue;
    const st = [p], c = [];
    seen.add(p);
    while (st.length) {
      const x = st.pop();
      c.push(x);
      for (const q of g.adj.get(x)) if (!seen.has(q)) { seen.add(q); st.push(q); }
    }
    out.push(c.sort((a, b) => (g.cnt.get(b) - g.cnt.get(a)) || cmp(a, b)));
  }
  return out.sort((a, b) => b.length - a.length);
}

// ---------------------------------------------------------------- 時間の軸
const fmtDate = d => recDate(d) || d;   // 記録の日付の形（起案者の指示 2026-10-24。row.recDate）

function peopleJoin(names, limit = 4) {
  if (names.length <= limit) return names.map(E).join('、');
  return names.slice(0, limit).map(E).join('、') + ` ほか ${names.length - limit} 名`;
}

function stageNote(r, addedNodes, nAddedEdges, cutAdded, cutRemoved, merged, first, newCluster) {
  const a = anchor(r.key || '');
  const href = `${ROW_HREF}&amp;w=${E(a)}#w-${E(a)}`;
  const head = `<a href="${href}">${fmtDate(r.date)} ── ${E(r.title || '')}</a>`;
  const bits = [];
  if (addedNodes.length) bits.push(`つながりに${peopleJoin(addedNodes)}が加わりました`);
  if (merged) {
    const sizes = merged.map(o => `${o.size}名`).join('、');
    bits.push(`<b>それまで別々だった ${merged.length} つのグループ（${sizes}）が、`
      + 'この 1 本で 1 つになりました</b>');
  } else if (first) bits.push('<b>ここからつながりができました</b>');
  else if (newCluster) bits.push('<b>ほかとまだつながらない、新しいグループができました</b>');
  if (cutAdded.length) bits.push(`<b>${peopleJoin(cutAdded)}を外すと、つながりが分かれるようになりました</b>`);
  if (cutRemoved.length) bits.push(`<b>${peopleJoin(cutRemoved)}を外しても、つながりが分かれなくなりました</b>`);
  if (!bits.length) bits.push(`線が ${nAddedEdges} 本増えました`);
  return `<p class="pnstage">${head}<br>${bits.join('。')}。</p>`;
}

// Python sorts the people a stage adds by -works over a set, so equal counts come out in hash
// order (it changes from run to run). Here equal counts go by name.
const byWorks = (g, ps) => ps.sort((a, b) => (g.cnt.get(b) - g.cnt.get(a)) || cmp(a, b));
const minus = (xs, ys) => { const s = new Set(ys); return xs.filter(x => !s.has(x)); };

/** build(dated[:i]) for i = 1, 2, … as far as timeline() reads it (core, cuts, cnt, adj, edges),
 * plus `added`: the edge keys that build(dated[:i]) has and build(dated[:i-1]) has not, in the
 * order build(dated[:i]) inserts them. Python rebuilds the whole network for every record
 * (150 records ≈ 60 ms here); this adds one record at a time. Records sharing a key (build keeps
 * only the last one's people) fall back to rebuilding. */
function* prefixGraphs(dated) {
  if (new Set(dated.map(r => r.key)).size !== dated.length) {
    let prev = build([]);
    for (let i = 1; i <= dated.length; i++) {
      const gi = build(dated.slice(0, i));
      gi.added = [...gi.edges.keys()].filter(e => !prev.edges.has(e));
      yield gi;
      prev = gi;
    }
    return;
  }
  const cnt = new Map(), worksOf = new Map(), works = [], nodes = new Set(), edges = new Map(), adj = new Map();
  for (const r of dated) {
    const ps = new Set();
    for (const [role, person] of r.people || []) if (KEEP.has(role)) ps.add(person);
    const added = [];
    if (ps.size) {
      const wi = works.length;
      works.push(ps);
      const fresh = new Set();
      for (const p of ps) {
        const c = (cnt.get(p) || 0) + 1;
        cnt.set(p, c);
        if (!worksOf.has(p)) worksOf.set(p, []);
        worksOf.get(p).push(wi);
        if (c === MIN_WORKS) { fresh.add(p); nodes.add(p); adj.set(p, new Set()); }
      }
      // A new edge either has a newly counted person (all their works are looked at) or is
      // between two people already in, met in this record. Works go in order and pairs in
      // itertools.combinations(sorted(...)) order, so `added` comes out in build()'s order.
      const touched = new Set([wi]);
      for (const p of fresh) for (const w of worksOf.get(p)) touched.add(w);
      for (const w of [...touched].sort((x, y) => x - y)) {
        const s = [...works[w]].filter(p => nodes.has(p)).sort(cmp);
        for (let i = 0; i < s.length; i++) {
          for (let j = i + 1; j < s.length; j++) {
            const a = s[i], b = s[j];
            if (w !== wi && !fresh.has(a) && !fresh.has(b)) continue;
            const key = a + '\0' + b, e = edges.get(key);
            if (e) e[2]++;
            else { edges.set(key, [a, b, 1]); added.push(key); }
            adj.get(a).add(b);
            adj.get(b).add(a);
          }
        }
      }
    }
    const core = [...nodes].filter(p => adj.get(p).size).sort(cmp);
    yield {core, cuts: cuts(core, adj), cnt, adj, edges, added};
  }
}

/** people.timeline */
export function timeline(rated, g, idx) {
  const dated = rated.filter(r => r.date).sort((a, b) => cmp(a.date, b.date) || cmp(a.key, b.key));
  let prev = build([]);
  let prevComps = [];
  const stages = [];
  const unchanged = {no_credit: 0, repeat: 0, not_yet: 0};
  let i = 0;
  for (const gi of prefixGraphs(dated)) {
    const r = dated[i++];
    const addedNodes = byWorks(gi, minus(gi.core, prev.core));
    const addedEdges = gi.added;
    const cutAdded = minus(gi.cuts, prev.cuts).sort(cmp);
    const cutRemoved = minus(prev.cuts, gi.cuts).sort(cmp);
    const compsNow = components(gi).map(c => new Set(c));
    const changed = addedNodes.length || addedEdges.length || cutAdded.length || cutRemoved.length
      || compsNow.length !== prevComps.length;
    if (!changed) {
      const ps = new Set((r.people || []).filter(([role]) => KEEP.has(role)).map(([, p]) => p));
      const core = new Set(gi.core);
      if (!ps.size) unchanged.no_credit++;
      else if ([...ps].filter(p => core.has(p)).length >= 2) unchanged.repeat++;
      else unchanged.not_yet++;
      prev = gi; prevComps = compsNow;
      continue;
    }
    let merged = null;
    for (const nw of compsNow) {
      const olds = prevComps.filter(o => [...o].some(p => nw.has(p)));
      if (olds.length > 1) { merged = olds.sort((a, b) => b.size - a.size); break; }
    }
    const newCluster = merged === null && compsNow.length > prevComps.length;
    const first = newCluster && !prevComps.length;
    const note = stageNote(r, addedNodes, addedEdges.length, cutAdded, cutRemoved, merged, first,
                           newCluster && !first);
    stages.push({
      n: addedNodes.filter(p => idx.has(p)).map(p => idx.get(p)),
      e: addedEdges.map(k => gi.edges.get(k)).filter(([a, b]) => idx.has(a) && idx.has(b))
        .map(([a, b]) => [idx.get(a), idx.get(b)]),
      note, date: r.date, title: r.title || '',
      merged: merged ? merged.map(o => o.size) : [],
    });
    prev = gi; prevComps = compsNow;
  }
  const restNodes = byWorks(g, minus(g.core, prev.core));
  const restEdges = [...g.edges.keys()].filter(e => !prev.edges.has(e)).map(k => g.edges.get(k));
  stages.push({
    n: restNodes.filter(p => idx.has(p)).map(p => idx.get(p)),
    e: restEdges.filter(([a, b]) => idx.has(a) && idx.has(b)).map(([a, b]) => [idx.get(a), idx.get(b)]),
    note: '', date: '', title: '', merged: [],
  });
  return {stages, unchanged, n_dated: dated.length, n_undated: rated.length - dated.length,
          gap_people: restNodes.length};
}

/** A Python float inside the payloads (json.dumps prints 740.0, not 740). */
class F { constructor(v) { this.v = v; } }

/** json.dumps(x, ensure_ascii=False, separators=(",", ":")) */
function cdumps(x) {
  if (x instanceof F) return pyFloat(x.v);
  if (typeof x === 'number') return Number.isInteger(x) ? String(x) : pyFloat(x);
  if (typeof x === 'string') return JSON.stringify(x);
  if (Array.isArray(x)) return '[' + x.map(cdumps).join(',') + ']';
  return '{' + Object.entries(x).map(([k, v]) => JSON.stringify(k) + ':' + cdumps(v)).join(',') + '}';
}
const scriptSafe = raw => raw.replace(/</g, '\\u003c').replace(/&/g, '\\u0026');

// ---------------------------------------------------------------- 配置
const radius = (nWorks, mx) => 5.0 + 6.0 * Math.sqrt(nWorks / Math.max(mx, 1));

/** people.layout (+ _fit, _separate). Positions by core index: [xs, ys]. */
export function layout(g, iters = 460) {
  const ns = g.core, n = ns.length;
  if (!n) return [new Float64Array(0), new Float64Array(0)];
  const cx = W / 2, cy = H / 2, r0 = Math.min(W, H) / 2.4;
  const px = new Float64Array(n), py = new Float64Array(n);
  for (let i = 0; i < n; i++) {
    const [sn, cs] = circle(i, n);
    px[i] = cx + r0 * cs;
    py[i] = cy + r0 * sn;
  }
  const idx = new Map(ns.map((p, i) => [p, i]));
  const E2 = [...g.edges.values()], nE = E2.length;
  const EA = Int32Array.from(E2, e => idx.get(e[0])), EB = Int32Array.from(E2, e => idx.get(e[1]));
  const EW = Float64Array.from(E2, e => 1.0 + 0.30 * (e[2] - 1));     // 1.0 + 0.30 * (wgt - 1)
  const k = 1.15 * Math.sqrt(W * H / n), kk = k * k;
  const t0 = W / 8.0;
  const ddx = new Float64Array(n), ddy = new Float64Array(n);
  for (let it = 0; it < iters; it++) {
    const t = t0 * (1.0 - it / iters) + 0.4;
    ddx.fill(0); ddy.fill(0);
    for (let a = 0; a < n; a++) {
      for (let b = a + 1; b < n; b++) {
        const dx = px[a] - px[b], dy = py[a] - py[b];
        const d = Math.sqrt(dx * dx + dy * dy) || 0.01;
        const f = kk / d, fx = dx / d * f, fy = dy / d * f;   // k * k / d, dx / d * f, dy / d * f
        ddx[a] += fx;
        ddy[a] += fy;
        ddx[b] -= fx;
        ddy[b] -= fy;
      }
    }
    for (let e = 0; e < nE; e++) {
      const a = EA[e], b = EB[e];
      const dx = px[a] - px[b], dy = py[a] - py[b];
      const d = Math.sqrt(dx * dx + dy * dy) || 0.01;
      const f = d * d / k * EW[e], fx = dx / d * f, fy = dy / d * f;
      ddx[a] -= fx;
      ddy[a] -= fy;
      ddx[b] += fx;
      ddy[b] += fy;
    }
    for (let p = 0; p < n; p++) {
      ddx[p] += (cx - px[p]) * 0.016;
      ddy[p] += (cy - py[p]) * 0.016;
      const dx = ddx[p], dy = ddy[p];
      const d = Math.sqrt(dx * dx + dy * dy) || 0.01;
      const step = Math.min(d, t);
      px[p] += dx / d * step;
      py[p] += dy / d * step;
    }
  }
  fit(px, py);
  return separate(px, py, g);
}

function fit(px, py) {
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
  for (let i = 0; i < px.length; i++) {
    x0 = Math.min(x0, px[i]); x1 = Math.max(x1, px[i]);
    y0 = Math.min(y0, py[i]); y1 = Math.max(y1, py[i]);
  }
  const s = Math.min((W - 2 * PAD) / Math.max(x1 - x0, 1.0), (H - 2 * PAD) / Math.max(y1 - y0, 1.0));
  const ox = PAD + ((W - 2 * PAD) - (x1 - x0) * s) / 2;
  const oy = PAD + ((H - 2 * PAD) - (y1 - y0) * s) / 2;
  for (let i = 0; i < px.length; i++) {
    px[i] = ox + (px[i] - x0) * s;
    py[i] = oy + (py[i] - y0) * s;
  }
}

function separate(px, py, g, rounds = 220, gap = 3.0) {
  const ns = g.core, n = ns.length;
  const mx = Math.max(...g.nodes.map(p => g.cnt.get(p)));
  const rad = Float64Array.from(ns, p => radius(g.cnt.get(p), mx));
  for (let round = 0; round < rounds; round++) {
    let moved = 0.0;
    for (let a = 0; a < n; a++) {
      for (let b = a + 1; b < n; b++) {
        const dx = px[b] - px[a], dy = py[b] - py[a];
        const d = Math.sqrt(dx * dx + dy * dy) || 0.01;
        const need = rad[a] + rad[b] + gap;
        if (d >= need) continue;
        const push = (need - d) / 2;
        const sx = dx / d * push, sy = dy / d * push;          // ux * push, uy * push
        px[a] -= sx;
        py[a] -= sy;
        px[b] += sx;
        py[b] += sy;
        moved += push;
      }
    }
    for (let p = 0; p < n; p++) {
      px[p] = Math.min(Math.max(px[p], rad[p] + 2), W - rad[p] - 2);
      py[p] = Math.min(Math.max(py[p], rad[p] + 2), H - rad[p] - 2);
    }
    if (moved < 0.4) break;
  }
  return [px, py];
}

/** people.place_labels: [[core index, x, y, anchor]] */
function placeLabels(g, px, py, rad) {
  const ns = g.core;
  const cutSet = new Set(g.cuts);
  const order = ns.map((p, i) => i).sort((i, j) => {
    const a = ns[i], b = ns[j];
    return (cutSet.has(b) - cutSet.has(a)) || (g.cnt.get(b) - g.cnt.get(a)) || cmp(a, b);
  });
  const placed = [], out = [];
  const h = 15.0;
  for (const i of order) {
    const p = ns[i];
    if (out.length >= LABEL_MAX && !cutSet.has(p)) break;
    const x = px[i], y = py[i], r = rad[i], w = textW(p);
    const cands = [[r + 5, 0, 'start'], [-(r + 5), 0, 'end'],
                   [0, -(r + 11), 'middle'], [0, r + 11, 'middle'],
                   [r + 4, -(r + 8), 'start'], [-(r + 4), -(r + 8), 'end'],
                   [r + 4, r + 8, 'start'], [-(r + 4), r + 8, 'end']];
    for (const [ox, oy, anc] of cands) {
      const ax = x + ox;
      const x0 = anc === 'start' ? ax : (anc === 'end' ? ax - w : ax - w / 2);
      const box = [x0, y + oy - h / 2, x0 + w, y + oy + h / 2];
      if (box[0] < 1 || box[2] > W - 1 || box[1] < 1 || box[3] > H - 1) continue;
      if (placed.some(b => b[0] < box[2] && box[0] < b[2] && b[1] < box[3] && box[1] < b[3])) continue;
      let hit = false;
      for (let q = 0; q < ns.length; q++) {
        if (q !== i && Math.abs(px[q] - (box[0] + box[2]) / 2) < (box[2] - box[0]) / 2 + rad[q]
            && Math.abs(py[q] - y - oy) < h / 2 + rad[q]) { hit = true; break; }
      }
      if (hit) continue;
      placed.push(box);
      out.push([i, ax, y + oy, anc]);
      break;
    }
  }
  return out;
}

const isMaker = (g, p) => [...g.roles.get(p)].some(r => MAKER.has(r));

function payload(g, px, py, rad, idx) {
  const cutSet = new Set(g.cuts);
  const nodes = g.core.map((p, i) => ({
    n: p, w: g.cnt.get(p), d: g.adj.get(p).size, m: isMaker(g, p) ? 1 : 0, c: cutSet.has(p) ? 1 : 0,
    x: new F(pyRound(px[i], 1)), y: new F(pyRound(py[i], 1)), r: new F(pyRound(rad[i], 1)),
    t: g.titles.get(p).map(([t, k]) => [t, anchor(k)]),
  }));
  const edges = [...g.edges.values()].map(([a, b, w]) => [idx.get(a), idx.get(b), w]);
  return scriptSafe(cdumps({w: new F(W), h: new F(H), pad: new F(PAD), nodes, edges}));
}

// ---------------------------------------------------------------- 読み（規則）
// people.py の read_facts / READ_SCORE / _sentence / reading / read_block と同じ規則・同じ文。
// 何を言うかは点数で選び、名前は網の点からしか取らない（LLM は呼ばない ── 持ち主の指示
// 2026-10-18）。記録を 1 回なめる足し算と点・線の並べ替えだけで、D1 も外部も読まない。
export const READ_PICK = 3, RECENT_YEARS = 2, RECENT_MIN = 2, LONG_MIN = 3;
export const READ_ORDER = ['shape', 'top', 'bridge', 'pair', 'merge', 'started', 'recent', 'long', 'mix'];
const yearOf = d => (/^[0-9]{4}/.test(d) ? parseInt(d.slice(0, 4), 10) : null);
const ysMin = ys => Math.min(...ys.keys()), ysMax = ys => Math.max(...ys.keys());

/** people.read_facts */
export function readFacts(rated, g, comps, tl) {
  const nodes = new Set(g.nodes), years = new Map(), allYears = [];
  for (const r of rated) {
    const y = yearOf(r.date || '');
    if (y === null) continue;
    const ps = new Set((r.people || []).filter(([role]) => KEEP.has(role)).map(([, p]) => p));
    if (!ps.size) continue;
    allYears.push(y);
    for (const p of ps) {
      if (!nodes.has(p)) continue;
      if (!years.has(p)) years.set(p, new Map());
      const ys = years.get(p);
      ys.set(y, (ys.get(y) || 0) + 1);
    }
  }
  const cnt = p => g.cnt.get(p), deg = p => g.adj.get(p).size;
  const splits = new Map(g.cuts.map(p => [p, components(g, [p]).length]));
  const core = [...g.core].sort((a, b) => (cnt(b) - cnt(a)) || cmp(a, b));
  const top = core.length ? core[0] : null;
  let bridge = null;
  for (const p of [...g.cuts].sort((a, b) => (splits.get(b) - splits.get(a)) || (deg(b) - deg(a)) || cmp(a, b))) {
    if (p !== top) { bridge = {name: p, splits: splits.get(p), people: deg(p)}; break; }
  }
  let pair = null;
  const heavy = [...g.edges.values()].sort((x, y) => (y[2] - x[2]) || cmp(x[0], y[0]) || cmp(x[1], y[1]));
  if (heavy.length && heavy[0][2] >= 2) {
    const [a, b, w] = heavy[0];
    const wt = (x, y) => g.edges.get(cmp(x, y) < 0 ? x + '\0' + y : y + '\0' + x)[2];
    const ab = g.adj.get(b);
    const third = [...g.adj.get(a)].filter(q => ab.has(q)).map(q => [Math.min(wt(a, q), wt(b, q)), q])
      .sort((x, y) => (y[0] - x[0]) || (cnt(y[1]) - cnt(x[1])) || cmp(x[1], y[1]));
    const [c, m] = third.length && third[0][0] >= 2 ? [third[0][1], third[0][0]] : ['', 0];
    pair = {a, b, w, c, m};
  }
  let merge = null;
  const sum = xs => xs.reduce((s, x) => s + x, 0);
  for (const s of tl.stages) {
    if (s.merged && s.merged.length && (merge === null || sum(s.merged) > sum(merge.sizes))) {
      merge = {date: s.date, title: s.title, sizes: [...s.merged]};
    }
  }
  const started = tl.stages.length && tl.stages[0].date ? {date: tl.stages[0].date, title: tl.stages[0].title} : null;
  let recent = null;
  if (allYears.length && Math.max(...allYears) - Math.min(...allYears) >= RECENT_YEARS) {
    const y1 = Math.max(...allYears) - RECENT_YEARS + 1, got = [];
    for (const [p, ys] of years) {
      let n = 0;
      for (const [y, k] of ys) if (y >= y1) n += k;
      if (ysMin(ys) >= y1 && n >= RECENT_MIN) got.push([p, n]);
    }
    got.sort((x, y) => (y[1] - x[1]) || (cnt(y[0]) - cnt(x[0])) || cmp(x[0], y[0]));
    if (got.length) recent = {from: y1, people: got.slice(0, 3)};
  }
  let long = null;
  const spans = [...years].filter(([p]) => p !== top).map(([p, ys]) => [ysMax(ys) - ysMin(ys) + 1, p])
    .filter(t => t[0] >= LONG_MIN).sort((x, y) => (y[0] - x[0]) || (cnt(y[1]) - cnt(x[1])) || cmp(x[1], y[1]));
  if (spans.length) {
    const p = spans[0][1], ys = years.get(p);
    long = {name: p, first: ysMin(ys), last: ysMax(ys)};
  }
  return {
    n_core: g.core.length, bundles: comps.map(c => c.length),
    top: top === null ? null : {name: top, role: isMaker(g, top) ? '作り手' : '出演', works: cnt(top), splits: splits.get(top) || 0},
    bridge, pair, merge, started, recent, long,
    mix: {n: g.nodes.length, makers: g.nodes.filter(p => isMaker(g, p)).length},
  };
}

const sizes = (xs, sep) => xs.map(s => `${s} 名`).join(sep);

/** people.READ_SCORE ── 何を言うかを決める点数（0 は言わない）。 */
export function readScore(kind, f) {
  if (kind === 'bridge' && f.bridge) return 70 + 5 * f.bridge.splits;
  if (kind === 'pair' && f.pair) return 40 + 10 * Math.min(f.pair.w, 6) + (f.pair.c ? 5 : 0);
  if (kind === 'merge' && f.merge) return 50 + Math.floor(Math.min(f.merge.sizes.reduce((s, x) => s + x, 0), 40) / 2);
  if (kind === 'started' && f.started && !f.merge) return 30;
  if (kind === 'recent' && f.recent) return 45 + 5 * f.recent.people.length;
  if (kind === 'long' && f.long) return 35 + 5 * Math.min(f.long.last - f.long.first + 1, 8);
  if (kind === 'mix' && f.mix.n) {
    const m = f.mix.makers, n = f.mix.n;
    return 3 * m >= n || 10 * m <= n ? 40 : 20;
  }
  return 0;
}

function sentence(kind, f) {
  if (kind === 'shape') {
    const b = f.bundles;
    if (b.length === 1) return `線を持つ ${f.n_core} 名は、みなひと続きのグループにつながっています。`;
    const more = b.length > 4 ? ` ほか ${b.length - 4} つ` : '';
    return `グループは ${b.length} つで、大きい順に ${sizes(b.slice(0, 4), '・')}${more}です。`;
  }
  if (kind === 'top') {
    const t = f.top;
    let s = `いちばんよく名前が出てくるのは${t.name}さん（${t.role}）で、${t.works} 作品に出ています。`;
    if (t.splits) s += `外すとつながりが ${t.splits} つに分かれる人でもあります。`;
    return s;
  }
  if (kind === 'bridge') {
    const b = f.bridge;
    return `${b.name}さんを外すと、つながりが ${b.splits} つに分かれます。`
      + `${b.name}さんを通して、別々の顔ぶれがつながっています。`;
  }
  if (kind === 'pair') {
    const p = f.pair;
    if (p.c) return `${p.a}さん・${p.b}さん・${p.c}さんは、どの 2 人をとっても ${p.m} 本以上で一緒に出ています。`;
    return `${p.a}さんと${p.b}さんは ${p.w} 本で一緒に出ていて、いちばんよく一緒になる組み合わせです。`;
  }
  if (kind === 'merge') {
    const m = f.merge, what = m.title ? `「${m.title}」` : '公演';
    return `${fmtDate(m.date)}の${what}で、別々だった ${m.sizes.length} つのグループ`
      + `（${sizes(m.sizes, '、')}）が 1 つになりました。`;
  }
  if (kind === 'started') {
    const s = f.started, what = s.title ? `「${s.title}」` : '公演';
    return `つながりは ${fmtDate(s.date)}の${what}から始まりました。`;
  }
  if (kind === 'recent') {
    const r = f.recent, names = r.people.map(([p, n]) => `${p}さん（${n} 本）`).join('、');
    return `${r.from} 年からの ${RECENT_YEARS} 年で新しくよく名前が出てくるのは、${names}です。`;
  }
  if (kind === 'long') {
    const x = f.long;
    return `${x.name}さんは ${x.first} 年から ${x.last} 年まで、${x.last - x.first + 1} 年にわたって名前が出てきます。`;
  }
  if (kind === 'mix') {
    const m = f.mix.makers, n = f.mix.n;
    if (3 * m >= n) return `2 作品以上で出てくる ${n} 名のうち、作り手（演出・脚本ほか）が ${m} 名います。`
      + '出演者だけでなく、作り手の名前もよく重なっています。';
    if (!m) return `2 作品以上で出てくる ${n} 名は、みな出演者です。`;
    if (10 * m <= n) return `2 作品以上で出てくる ${n} 名のうち、作り手（演出・脚本ほか）は ${m} 名で、`
      + '重なるのはほとんどが出演者です。';
    return `2 作品以上で出てくる ${n} 名のうち、出演が ${n - m} 名、作り手（演出・脚本ほか）が ${m} 名です。`;
  }
  return '';
}

/** people.reading */
export function reading(f) {
  if (!f.top) return [];
  const scored = READ_ORDER.slice(2).map((k, i) => [readScore(k, f), i + 2, k])
    .sort((x, y) => (y[0] - x[0]) || (x[1] - y[1]));
  const pick = new Set(['shape', 'top', ...scored.slice(0, READ_PICK).filter(([s]) => s > 0).map(([, , k]) => k)]);
  return READ_ORDER.filter(k => pick.has(k)).map(k => sentence(k, f));
}

/** people.read_block */
export function readBlock(rated, g, comps, tl) {
  const lines = reading(readFacts(rated, g, comps, tl));
  if (!lines.length) return '';
  return '<div class="pread"><h3>この図から分かること</h3>'
    + `<p>${E(lines.join(''))}</p>`
    + '<p class="pnote">この文章は、上のグループの形と数字だけから、決まった手順で'
    + '作っています。記録が変わると、開くたびに書き直されます。</p></div>';
}

// ---------------------------------------------------------------- 図
/** people.panel(rated, owner=False) */
export function panel(rated) {
  if (!rated || !rated.length) return '';
  const g = build(rated);
  if (g.core.length < 3) return '';
  const [px, py] = layout(g);
  const comps = components(g);
  const mx = Math.max(...g.nodes.map(p => g.cnt.get(p)));
  const cutSet = new Set(g.cuts);
  const ns = g.core;
  const idx = new Map(ns.map((p, i) => [p, i]));
  const rad = ns.map(p => radius(g.cnt.get(p), mx));

  const lines = [...g.edges.values()].sort((a, b) => b[2] - a[2]).map(([a, b, wgt]) => {
    const i = idx.get(a), j = idx.get(b);
    return `<line data-a="${i}" data-b="${j}"`
      + ` x1="${f1(px[i])}" y1="${f1(py[i])}" x2="${f1(px[j])}" y2="${f1(py[j])}"`
      + ` stroke-width="${fmt(0.9 + 0.85 * (wgt - 1), 2)}"`
      + ` stroke-opacity="${fmt(Math.min(0.13 + 0.15 * wgt, 0.80), 2)}">`
      + `<title>${E(a)} と ${E(b)} ── 同じ作品 ${wgt} 本で一緒でした</title></line>`;
  });

  const dots = ns.map((p, i) => i).sort((i, j) => g.cnt.get(ns[i]) - g.cnt.get(ns[j])).map(i => {
    const p = ns[i], maker = isMaker(g, p), tl = g.titles.get(p);
    const ts = tl.slice(0, 4).map(([t]) => t).join('／');
    const more = tl.length > 4 ? ` ほか ${tl.length - 4} 本` : '';
    return `<g class="nd${cutSet.has(p) ? ' cut' : ''}" data-i="${i}">`
      + `<title>${E(p)}（${maker ? '作り手' : '出演'}）── 観た作品 ${g.cnt.get(p)} 本・`
      + `共演した人 ${g.adj.get(p).size} 名／${E(ts)}${E(more)}</title>`
      + `<circle cx="${f1(px[i])}" cy="${f1(py[i])}" r="${f1(rad[i])}"`
      + ` fill="var(--${maker ? 's2' : 's1'})"/></g>`;
  });

  const labs = placeLabels(g, px, py, rad).map(([i, x, y, anc]) =>
    `<text class="nl" data-i="${i}" x="${f1(x)}" y="${f1(y)}"`
    + ` text-anchor="${anc}">${E(ns[i])}</text>`).join('');

  const cutsByDeg = [...g.cuts].sort((a, b) => g.adj.get(b).size - g.adj.get(a).size);
  const cutBtns = cutsByDeg.map(p =>
    `<button data-cut="${idx.get(p)}">${E(p)}<span class="cn">`
    + `${components(g, [p]).length} つに分かれる</span></button>`).join('');
  const cutTxt = !g.cuts.length ? 'このつながりには、外すとグループが分かれる人がいません。'
    : `<b>外すとつながりが分かれるのは、この ${g.cuts.length} 名です。</b>`
      + '名前を押すと、その人を図から外したときに残りがどう分かれるかが出ます。';

  const isoTxt = !g.isolated.length ? ''
    : `<br>2 作品以上に出てきますが、<b>ほかの誰とも一緒になっていない人が `
      + `${g.isolated.length} 名います</b>（`
      + g.isolated.map(E).join('、') + '）。共演の線がないので、図には出ていません。';

  const rows = [...g.nodes].sort((a, b) => (g.cnt.get(b) - g.cnt.get(a)) || cmp(a, b)).map(p =>
    [p, isMaker(g, p) ? '作り手' : '出演', g.cnt.get(p), g.adj.get(p).size,
     g.titles.get(p).map(([t]) => t).join('／')]);
  const table = chTable(['人', '役', '観た作品', '共演した人', '作品名'], rows);

  const data = payload(g, px, py, rad, idx);
  const tl = timeline(rated, g, idx);
  const readHtml = readBlock(rated, g, comps, tl);
  const tdata = scriptSafe(cdumps({stages: tl.stages}));
  const nStages = tl.stages.length - 1;
  const u = tl.unchanged;
  const nUnchanged = u.no_credit + u.repeat + u.not_yet;
  const gapTxt = `上演日が分からない記録が ${tl.n_undated} 件あります。時間の上に置けないので、`
    + `さかのぼるとこの分（${tl.gap_people} 名）はつながりから外れます。`
    + '<a href="/records/works?t=__TAGURI_TOKEN__">日記帳</a>の「公演詳細を直す」から'
    + '日付を入れると載ります。';
  const unchangedTxt = `このつまみに出るのは、つながりが変わった ${nStages} 件です。<b>残り ${nUnchanged} 件は`
    + '観た日につながりが変わらなかった公演です。</b>'
    + `${u.not_yet} 件はそのときまだ 1 回しか観ていない人ばかりの公演です`
    + '（同じ人をもう 1 本観た日に、図に入りました）。'
    + `${u.repeat} 件は同じ顔ぶれをもう一度観た公演、${u.no_credit} 件は出演者が`
    + '取れていない公演です。'
    + '1 件ずつは<a href="/records/works?t=__TAGURI_TOKEN__">日記帳</a>で読めます。';
  const timeBlock = nStages ? `<div class="ptime">
<div class="ptrow">
<button type="button" class="ptplay" data-pplay>▶ はじめから見る</button>
<input type="range" class="ptsl" data-psl min="0" max="${nStages}" value="${nStages}"
 aria-label="観た順に、つながりがどう広がったかを見る">
</div>
<div data-pnstage aria-live="polite"></div>
<p class="lead ptgap" data-pgap hidden>${gapTxt}</p>
<p class="lead">${unchangedTxt}</p>
<script type="application/json" data-pnet-time>${tdata}</script>
</div>` : '';
  return `<section class="card wide">
${h2('user', '一緒に出てくる人のつながり ── グループをつないでいるのは誰か',
     `<span class="badge part">${ns.length} 名・クレジットを取れた ${g.n_works} 作品</span>`)}
<p class="lead">同じ作品に出ていた人どうしを線で結んでいます。<b>2 作品以上で出てきた
${g.nodes.length} 名のうち、線を持つ ${ns.length} 名</b>を出しています
（全員は ${g.n_people} 名です）。${isoTxt}</p>
<p class="lead">この図で分かるのは、<b>グループがいくつあるか</b>と、
<b>どの人がグループをつないでいるか</b>です。
いまは線を持つ ${ns.length} 名が
<b>${comps.length === 1 ? 'ひと続きのグループです' : `${comps.length} 個のグループに分かれています`}</b>。
${cutTxt}</p>
${readHtml}
${timeBlock}
<div class="pcut">${cutBtns}
<button data-cut="reset" class="rst" hidden>全員を戻す</button></div>
<p class="psaid" data-psaid aria-live="polite"></p>
<div class="pnet" data-pnet>
<svg viewBox="0 0 ${fmtF(W, 0)} ${fmtF(H, 0)}" width="100%" role="img"
 aria-label="一緒に出てくる人のつながり">
<g class="ed" stroke="var(--base)">${lines.join('')}</g>
<g class="nds">${dots.join('')}</g>
<g class="nls">${labs}</g></svg>
<div class="ptip" data-ptip hidden></div>
<script type="application/json" data-pnet-data>${data}</script></div>
<p class="pkey"><span class="ky"><span class="sw s1"></span>出演</span>
<span class="ky"><span class="sw s2"></span>作り手（演出・脚本ほか）</span>
<span class="ky"><span class="sw ring"></span>外すとグループが分かれる人</span>
<span class="ky">点の大きさ ＝ 観た作品数</span>
<span class="ky">線の太さ ＝ 共演した作品数</span></p>
<p class="lead"><b>点はつまんで動かせます。</b>触れるとその人の線だけが浮きます。
下の表の行に触れても、同じところが浮きます。評価は色にも大きさにも入れていません。
気になる人がいたら、<a href="/recommend/favourites?t=__TAGURI_TOKEN__">お気に入り</a>に
名前で登録してください。<br>
<b>作り手が分かったのは、評価済み ${g.n_rated} 作品のうち ${g.n_works} 件です。</b>
残り ${g.n_rated - g.n_works} 件はこの図に入っていません。出演者と作り手（演出・脚本ほか）
だけを数え、制作・宣伝などの役職は入れていません。図に名前を書いたのは
${LABEL_MIN} 作品以上の人と、グループをつないでいる人だけです。ほかの人は点に触れると名前が出ます。</p>
${table}</section>`;
}
