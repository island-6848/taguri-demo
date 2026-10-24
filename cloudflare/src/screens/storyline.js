// 記録を見返す ▸ Storyline（前の名前「同じ作品で一緒だった人の流れ」、起案者の指示 2026-10-24「Storyline に名前を変えて」）: tools/taguri/storyline.py's panel() ported to
// the Worker. storyline.test.js checks panel() against storyline.panel byte for byte.
//
// Python behaviour copied on purpose:
// - sum() of floats is Neumaier-compensated since Python 3.12 (pySum below), so the layout's
//   heights come out to the same bits.
// - json.dumps prints a float that happens to be whole as "3.0"; floats in the payload are
//   wrapped in F so jd() can tell them from ints.
// - compact()'s neighbour list only ever holds the frames at t-1 and t+1 (frames are indexed by
//   t), so it reads those two directly instead of scanning every frame (same values, same order).
// Rewritten for CPU (Workers Free: 10 ms a request), each giving Python's exact result:
// names as integer ids with typed arrays; _reorder's candidates counted incrementally instead
// of rebuilt; neighbouring frames' crossings cached; worlds_of's pairwise union replaced by a
// union through each person's first session; a str compare without Array.from.
import {E, pyFloat, slice} from './py.js';
import {h2} from './icons.js';
import {anchor} from './anchor.js';
import {STORYLINE_JS} from './storyline_js.js';

export const MIN_TIMES = 4;
const BAND_PAD = 34.0;
const ALPHA = 0.1, BETA = 1.0, SWEEPS = 20, LINE_W = 2.8;
const D_IN = 3 * LINE_W, D_OUT = 9 * LINE_W;
const SNAP = 4.0;
const MIN_GAP = 54.0, PX_PER_DAY = 0.8, LEFT_PX = 84.0;
const RUN_PX = 7.0;
const ROW_HREF = '/records/works?t=__TAGURI_TOKEN__';

// ---------------------------------------------------------------- Python helpers
/** A float for jd(): json.dumps keeps "3.0" where JS would print "3". */
class F { constructor(v) { this.v = v; } }
const f = v => new F(v);
/** repr(float), with the common cases first (pyFloat does the exponent forms). */
function fl(v) {
  if (Number.isInteger(v) && Math.abs(v) < 1e16) return Object.is(v, -0) ? '-0.0' : v + '.0';
  const s = String(v);
  return s.includes('e') || !Number.isFinite(v) ? pyFloat(v) : s;
}
const strMemo = new Map();
/** json.dumps of a str (memoised: the same dates and names come back thousands of times). */
function js(x) {
  let s = strMemo.get(x);
  if (s === undefined) { s = JSON.stringify(x); if (strMemo.size > 50000) strMemo.clear(); strMemo.set(x, s); }
  return s;
}
/** json.dumps(x, ensure_ascii=False) with F for floats. */
function jd(x) {
  if (x instanceof F) return fl(x.v);
  if (x instanceof Pts) return jdPts(x.pts);
  if (x === null || x === undefined) return 'null';
  if (x === true) return 'true';
  if (x === false) return 'false';
  if (typeof x === 'number') return Number.isInteger(x) ? String(x) : fl(x);
  if (typeof x === 'string') return js(x);
  let out;
  if (Array.isArray(x)) {
    out = '[';
    for (let i = 0; i < x.length; i++) out += (i ? ', ' : '') + jd(x[i]);
    return out + ']';
  }
  out = '{';
  let first = true;
  if (x instanceof Map) {
    for (const [k, v] of x) { out += (first ? '' : ', ') + js(k) + ': ' + jd(v); first = false; }
  } else {
    for (const k in x) { out += (first ? '' : ', ') + js(k) + ': ' + jd(x[k]); first = false; }
  }
  return out + '}';
}
/** A line's points, the bulk of the payload: {"date": …, "y": float, "on": bool}. */
class Pts { constructor(pts) { this.pts = pts; } }
function jdPts(pts) {
  let out = '[';
  for (let i = 0; i < pts.length; i++) {
    const p = pts[i];
    out += (i ? ', {"date": ' : '{"date": ') + js(p.date) + ', "y": ' + fl(p.y) + (p.on ? ', "on": true}' : ', "on": false}');
  }
  return out + ']';
}

/** sum() of floats (CPython >= 3.12: Neumaier compensation, started from the first item). */
function pySum(xs) {
  if (!xs.length) return 0;
  let s = 0 + xs[0], c = 0.0;
  for (let i = 1; i < xs.length; i++) {
    const x = xs[i], t = s + x;
    if (Math.abs(s) >= Math.abs(x)) c += (s - t) + x; else c += (x - t) + s;
    s = t;
  }
  if (c && Number.isFinite(c)) s += c;
  return s;
}

/** Python's str order (code points) without py.cmp's Array.from per comparison: compare
 * UTF-16 units, moving surrogates (code points >= U+10000) above U+E000..U+FFFF. */
function cmp(a, b) {
  if (a === b) return 0;
  const n = Math.min(a.length, b.length);
  for (let i = 0; i < n; i++) {
    let x = a.charCodeAt(i), y = b.charCodeAt(i);
    if (x !== y) {
      if (x >= 0xD800 && y >= 0xD800) { x = x >= 0xE000 ? x - 0x800 : x + 0x2000; y = y >= 0xE000 ? y - 0x800 : y + 0x2000; }
      return x < y ? -1 : 1;
    }
  }
  return a.length < b.length ? -1 : 1;
}
const sortStr = xs => xs.slice().sort(cmp);
/** sorted(xs, key=lambda x: x[k]) for a str field (Array.prototype.sort is stable). */
const sortByStr = (xs, key) => xs.slice().sort((a, b) => cmp(key(a), key(b)));

/** date.fromisoformat(s).toordinal()-like day number, or null when it raises. */
function ordinal(s) {
  if (typeof s !== 'string') return null;
  const m = s.match(/^(\d{4})-(\d{2})-(\d{2})$/) || s.match(/^(\d{4})(\d{2})(\d{2})$/);
  if (!m) return null;
  const [y, mo, d] = [Number(m[1]), Number(m[2]), Number(m[3])];
  const dim = [31, (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0 ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  if (y < 1 || mo < 1 || mo > 12 || d < 1 || d > dim[mo - 1]) return null;
  const dt = new Date(0);
  dt.setUTCFullYear(y, mo - 1, d);
  return Math.round(dt.getTime() / 86400000);
}
function isoOf(ord) {
  const dt = new Date(ord * 86400000);
  return String(dt.getUTCFullYear()).padStart(4, '0') + '-' + String(dt.getUTCMonth() + 1).padStart(2, '0')
    + '-' + String(dt.getUTCDate()).padStart(2, '0');
}
const hasDate = r => ordinal(r.date || '') !== null;

// ---------------------------------------------------------------- sessions and worlds
/** storyline.sessions_of */
export function sessionsOf(rated, minTimes = MIN_TIMES) {
  const dated = rated.filter(r => hasDate(r) && r.people && r.people.length);
  const n = new Map();
  for (const r of dated) for (const p of new Set(r.people.map(x => x[1]))) n.set(p, (n.get(p) || 0) + 1);
  const keep = new Set([...n].filter(([, v]) => v >= minTimes).map(([p]) => p));
  const out = [];
  for (const r of sortByStr(dated, x => x.date)) {
    const ms = sortStr([...new Set(r.people.map(x => x[1]))].filter(p => keep.has(p)));
    if (ms.length) out.push({date: r.date, titles: [r.title], anchors: [anchor(r.key)], members: ms});
  }
  return [mergeSameDay(out), keep];
}

function mergeSameDay(sessions) {
  const out = [];
  for (const s of sessions) {
    let merged = false;
    for (const t of out) {
      if (t.date === s.date && t.members.some(m => s.members.includes(m))) {
        t.titles = t.titles.concat(s.titles);
        t.anchors = t.anchors.concat(s.anchors);
        t.members = sortStr([...new Set([...t.members, ...s.members])]);
        merged = true;
        break;
      }
    }
    if (!merged) out.push({...s});
  }
  return out;
}

/** storyline.worlds_of */
export function worldsOf(sessions) {
  const par = sessions.map((_, i) => i);
  const find = x => { while (par[x] !== x) { par[x] = par[par[x]]; x = par[x]; } return x; };
  // Python unions every pair of sessions that share someone. Uniting each session with the
  // first one each person appeared in gives the same components, and the groups below only
  // depend on the components (each is listed from its smallest index, in index order).
  const seen = new Map();
  for (let i = 0; i < sessions.length; i++) {
    for (const m of sessions[i].members) {
      if (seen.has(m)) { const a = find(i), b = find(seen.get(m)); if (a !== b) par[a] = b; } else seen.set(m, i);
    }
  }
  const g = new Map();
  for (let i = 0; i < sessions.length; i++) {
    const r = find(i);
    if (!g.has(r)) g.set(r, []);
    g.get(r).push(i);
  }
  return [...g.values()].sort((a, b) => b.length - a.length || cmp(sessions[a[0]].date, sessions[b[0]].date));
}

// ---------------------------------------------------------------- StoryFlow の 3 段
// The names of one world become integer ids in code-point order, so "sorted(names)" is a
// numeric sort and the ranks and heights live in typed arrays (the Worker has 10 ms of CPU).

/** storyline.frames_of, on ids. */
function framesOf(sessions, world) {
  const idx = sortByStr(world, i => sessions[i].date);
  const first = new Map(), last = new Map();
  idx.forEach((i, t) => {
    for (const m of sessions[i].members) { if (!first.has(m)) first.set(m, t); last.set(m, t); }
  });
  const names = sortStr([...first.keys()]);
  const id = new Map(names.map((m, k) => [m, k]));
  const P = names.length;
  const frames = idx.map((i, t) => {
    const mem = new Uint8Array(P);
    const members = sessions[i].members.map(m => id.get(m)).sort((a, b) => a - b);
    for (const m of members) mem[m] = 1;
    const transit = [], trn = new Uint8Array(P);
    for (let m = 0; m < P; m++) if (!mem[m] && first.get(names[m]) <= t && t <= last.get(names[m])) { transit.push(m); trn[m] = 1; }
    return {i, t, date: sessions[i].date, members, mem, transit, trn};
  });
  return [frames, names];
}

function rankOf(o, P) {
  const r = new Int32Array(P).fill(-1);
  for (let k = 0; k < o.length; k++) r[o[k]] = k;
  return r;
}

/** storyline._pair_crossings(ref, cur) with ra = the ranks of ref. */
function pairCrossings(ra, cur, buf) {
  let c = 0;
  for (let j = 0; j < cur.length; j++) { const r = ra[cur[j]]; if (r >= 0) buf[c++] = r; }
  let n = 0;
  for (let x = 0; x < c; x++) { const v = buf[x]; for (let y = x + 1; y < c; y++) if (v > buf[y]) n++; }
  return n;
}

/** storyline._reorder: returns _pair_crossings(ref, the new order); reordered() builds it.
 *
 * Python builds every out[:k] + blk + out[k:] and counts its crossings against ref. The
 * bundle's lines that are in ref come in ref's order, and so do the outside ones, so the only
 * crossings are (outside line, bundle line) pairs, and those change with k one line at a time:
 * moving out[k] from after the bundle to before it trades its "above" pairs (bundle lines
 * ranked after it) for its "below" pairs. Same counts and the same first minimum as Python,
 * without rebuilding and recounting every candidate. */
let BLK = new Int32Array(64), OUT = new Int32Array(64), BELOW = new Int32Array(64);
function reorder(frame, ref, rank) {
  const need = frame.members.length + frame.transit.length;
  if (BLK.length < need) { BLK = new Int32Array(2 * need); OUT = new Int32Array(2 * need); BELOW = new Int32Array(2 * need); }
  const blk = BLK, out = OUT, below = BELOW, mem = frame.mem, trn = frame.trn;
  let nBlk = 0, nOut = 0;
  for (let j = 0; j < ref.length; j++) {               // walking ref = sorting by rank
    const m = ref[j];
    if (mem[m]) blk[nBlk++] = m;
    else if (trn[m]) { below[nOut] = nBlk; out[nOut++] = m; }
  }
  const nb = nBlk, nIn = nOut;
  for (const m of frame.members) if (rank[m] < 0) blk[nBlk++] = m;   // then by name (= id)
  for (const m of frame.transit) if (rank[m] < 0) out[nOut++] = m;
  let n = 0;
  for (let j = 0; j < nIn; j++) n += nb - below[j];
  let bestK = 0, bestN = n;
  for (let k = 0; k < nOut; k++) {
    if (k < nIn) n += 2 * below[k] - nb;                // + below - above
    if (n < bestN) { bestN = n; bestK = k + 1; }
  }
  REORDER_K = bestK; REORDER_NB = nBlk; REORDER_NO = nOut;
  return bestN;
}
let REORDER_K = 0, REORDER_NB = 0, REORDER_NO = 0;
/** The order the last reorder() call chose: out[:k] + blk + out[k:]. */
function reordered() {
  const k = REORDER_K, c = new Array(REORDER_NB + REORDER_NO);
  let p = 0;
  for (let j = 0; j < k; j++) c[p++] = OUT[j];
  for (let j = 0; j < REORDER_NB; j++) c[p++] = BLK[j];
  for (let j = k; j < REORDER_NO; j++) c[p++] = OUT[j];
  return c;
}

/** storyline.order_sweep.
 *
 * The crossings between two neighbouring frames (count_crossings' term, _pair_crossings in
 * either direction: both count the discordant pairs of the lines live in both) are kept per
 * pair in C and only recounted when one of the two orders changes. reorder() already knows
 * the new count against the frame it was ordered from. */
function orderSweep(frames, P) {
  const order = frames.map(fr => fr.members.concat(fr.transit));     // t is the index
  const ranks = order.map(o => rankOf(o, P));
  const buf = new Int32Array(P);
  const C = new Int32Array(Math.max(frames.length - 1, 0));         // C[t]: frames t and t+1
  for (let t = 0; t + 1 < frames.length; t++) C[t] = pairCrossings(ranks[t], order[t + 1], buf);
  const total = () => { let n = 0; for (let t = 0; t < C.length; t++) n += C[t]; return n; };
  const first = total();
  let best = order.map(o => o.slice()), bestN = first;
  const sweep = seq => {
    for (let k = 1; k < seq.length; k++) {
      const t = seq[k].t, pt = seq[k - 1].t;
      const n = reorder(seq[k], order[pt], ranks[pt]);
      const pc = Math.min(t, pt);                                    // the pair (t, pt)
      if (n < C[pc]) {
        const cand = reordered(), r = ranks[t];
        r.fill(-1);
        for (let j = 0; j < cand.length; j++) r[cand[j]] = j;
        order[t] = cand; C[pc] = n;
        const ot = 2 * t - pt;                                       // the other neighbour
        if (ot >= 0 && ot < frames.length) {
          const po = Math.min(t, ot);
          C[po] = pairCrossings(ranks[ot], cand, buf);
        }
      }
    }
  };
  const rev = frames.slice().reverse();
  for (let k = 0; k < SWEEPS; k++) {
    sweep(k % 2 === 0 ? frames : rev);
    const n = total();
    if (n < bestN) { bestN = n; best = order.map(o => o.slice()); }
    if (bestN === 0) break;
  }
  return [best, bestN, first];
}

/** storyline.align_frames */
function alignFrames(frames, order) {
  const out = [];
  for (let k = 0; k + 1 < frames.length; k++) {
    const a = frames[k], b = frames[k + 1];
    const both = a.members.filter(m => b.mem[m]);              // ids ascending = sorted names
    if (!both.length) continue;
    const oa = order[a.t], ob = order[b.t], na = oa.length, nb = ob.length;
    let best = null, bestS = -1.0;
    for (const m of both) {
      const ra = oa.indexOf(m) / Math.max(na - 1, 1);
      const rb = ob.indexOf(m) / Math.max(nb - 1, 1);
      const sc = both.length + ALPHA * (1.0 - Math.abs(ra - rb));
      if (sc > bestS) { bestS = sc; best = m; }
    }
    out.push([a.t, b.t, best]);
  }
  return out;
}

/** storyline._gaps */
function gapsOf(frame, o) {
  const mem = frame.mem, g = new Float64Array(Math.max(o.length - 1, 0));
  for (let k = 0; k + 1 < o.length; k++) g[k] = mem[o[k]] && mem[o[k + 1]] ? D_IN : D_OUT;
  return g;
}

/** The running sums of _gaps (the z = y - cum shift _project makes), per frame. */
function cumOf(frame, o) {
  const g = gapsOf(frame, o), cum = new Float64Array(o.length);
  let acc = 0.0;
  for (let k = 1; k < o.length; k++) { acc += g[k - 1]; cum[k] = acc; }
  return cum;
}

let SV = new Float64Array(64), SW = new Float64Array(64);
/** storyline._project (pool adjacent violators) given cumOf's sums; writes into out. */
function project(want, cum, out = new Float64Array(want.length)) {
  const n = want.length;
  if (SV.length < n) { SV = new Float64Array(2 * n); SW = new Float64Array(2 * n); }
  const sv = SV, sw = SW;
  let top = 0;
  for (let k = 0; k < n; k++) {
    sv[top] = want[k] - cum[k]; sw[top] = 1.0; top++;
    while (top > 1 && sv[top - 2] > sv[top - 1] - 1e-12) {
      const v2 = sv[top - 1], w2 = sw[top - 1], v1 = sv[top - 2], w1 = sw[top - 2];
      top -= 2;
      sv[top] = (v1 * w1 + v2 * w2) / (w1 + w2); sw[top] = w1 + w2; top++;
    }
  }
  let k = 0;
  for (let s = 0; s < top; s++) {
    const c = Math.round(sw[s]);        // the weights are whole numbers, no tie to break
    for (let j = 0; j < c; j++, k++) out[k] = sv[s] + cum[k];
  }
  return out;
}

/** storyline.compact: y[t][id] is the height (NaN where the line is not live). */
function compact(frames, order, aligns, P) {
  const y = frames.map(() => new Float64Array(P).fill(NaN));
  const cumAt = frames.map(fr => cumOf(fr, order[fr.t]));
  for (const fr of frames) {
    const o = order[fr.t], pos = Array.from(cumAt[fr.t]);     // the same running sums
    const mid = pySum(pos) / pos.length;
    o.forEach((m, k) => { y[fr.t][m] = pos[k] - mid; });
  }
  // (5b): the anchors that pin a line at frame b to its height at frame a (dict order).
  const pinAt = frames.map(() => []);
  for (const [a, b, m] of aligns) {
    const k = order[b].indexOf(m);
    if (k >= 0) pinAt[b].push([a, m, k]);
  }
  const want = frames.map(fr => new Float64Array(order[fr.t].length));
  const nw = frames.map(fr => new Float64Array(order[fr.t].length));
  const two = [0, 0];
  let it = 0;
  for (it = 1; it <= 600; it++) {
    let moved = 0.0;
    for (const fr of frames) {
      const t = fr.t, o = order[t], yt = y[t], w = want[t];
      const prev = y[t - 1], next = y[t + 1];
      for (let k = 0; k < o.length; k++) {
        const m = o[k];
        let c = 0;
        if (prev && !Number.isNaN(prev[m])) two[c++] = prev[m];
        if (next && !Number.isNaN(next[m])) two[c++] = next[m];
        // sum() of one or two floats: Neumaier's correction is exactly 0 for two terms
        w[k] = c === 0 ? 0.0 : (c === 1 ? 0 + two[0] : two[0] + two[1]) / (c + BETA);
      }
      for (const [a, m, k] of pinAt[t]) w[k] = y[a][m];
      const out = project(w, cumAt[t], nw[t]);
      for (let k = 0; k < o.length; k++) {
        const d = Math.abs(out[k] - yt[o[k]]);
        if (d > moved) moved = d;
        yt[o[k]] = out[k];
      }
    }
    if (moved < 1e-4) break;
  }
  if (it > 600) it = 600;
  hold(frames, order, y, cumAt);
  return [y, it];
}

let HB = new Float64Array(64), HO = new Float64Array(64);
/** storyline._hold */
function hold(frames, order, y, cumAt, rounds = 12) {
  const seq = new Map();
  for (const fr of frames) for (const m of order[fr.t]) { if (!seq.has(m)) seq.set(m, []); seq.get(m).push(fr.t); }
  for (let r = 0; r < rounds; r++) {
    let changed = false;
    for (const [m, ts] of seq) {
      for (let k = 0; k + 1 < ts.length; k++) {
        const a = ts[k], b = ts[k + 1];
        const d = Math.abs(y[b][m] - y[a][m]);
        if (d > 0.0 && d < SNAP) { y[b][m] = y[a][m]; changed = true; }
      }
    }
    for (const fr of frames) {
      const o = order[fr.t], yt = y[fr.t];
      const cur = HB.length >= o.length ? HB : (HB = new Float64Array(2 * o.length));
      for (let k = 0; k < o.length; k++) cur[k] = yt[o[k]];
      const fixed = project(cur.subarray(0, o.length), cumAt[fr.t], HO.length >= o.length ? HO : (HO = new Float64Array(2 * o.length)));
      for (let k = 0; k < o.length; k++) yt[o[k]] = fixed[k];
    }
    if (!changed) break;
  }
}

/** storyline.layout: placed frames carry names again (pos in the frame's order). */
function layout(sessions, world) {
  const [frames, names] = framesOf(sessions, world);
  const P = names.length;
  const [order, nCross, nFirst] = orderSweep(frames, P);
  const aligns = alignFrames(frames, order);
  const [y, nIter] = compact(frames, order, aligns, P);
  let lo = Infinity;
  for (const fr of frames) for (const m of order[fr.t]) if (y[fr.t][m] < lo) lo = y[fr.t][m];
  const placed = [];
  let hi = -Infinity;
  for (const fr of frames) {
    const pos = new Map();
    for (const m of order[fr.t]) {
      const v = y[fr.t][m] - lo;
      pos.set(names[m], v);
      if (v > hi) hi = v;
    }
    placed.push({i: fr.i, t: fr.t, date: fr.date, members: fr.members.map(m => names[m]),
                 memberSet: new Set(fr.members.map(m => names[m])), pos,
                 bundle: fr.members.map(m => pos.get(names[m]))});
  }
  return {placed, height: hi - lo, nPeople: P,
          crossBefore: nFirst, crossAfter: nCross, nAligned: aligns.length, compactIters: nIter};
}

// ---------------------------------------------------------------- 横の位置
function xmap(dates) {
  const xs = new Map();
  if (!dates.length) return [xs, LEFT_PX];
  const ds = sortStr([...new Set(dates)]);
  let cur = LEFT_PX;
  xs.set(ds[0], cur);
  for (let k = 0; k + 1 < ds.length; k++) {
    const days = ordinal(ds[k + 1]) - ordinal(ds[k]);
    cur += Math.max(MIN_GAP, days * PX_PER_DAY);
    xs.set(ds[k + 1], cur);
  }
  return [xs, cur + LEFT_PX / 2];
}

/** storyline.build (floats wrapped in F where the payload prints them). */
export function build(rated, minTimes = MIN_TIMES) {
  const [sessions, keep] = sessionsOf(rated, minTimes);
  if (!sessions.length) return {locations: [], lines: [], sessions: [], from: '', to: ''};
  const locations = [], lines = [], ses = [];
  let top = 0.0;
  worldsOf(sessions).forEach((w, wi) => {
    const lay = layout(sessions, w);
    const placed = lay.placed;
    const per = new Map();
    for (const p of placed) {
      for (const [m, yy] of p.pos) {
        if (!per.has(m)) per.set(m, []);
        per.get(m).push({date: p.date, y: yy + top, on: p.memberSet.has(m)});
      }
    }
    for (const m of sortStr([...per.keys()])) {
      const pts = sortByStr(per.get(m), x => x.date);
      lines.push({name: m, loc: wi, pts, n: pts.filter(x => x.on).length,
                  from: pts[0].date, to: pts[pts.length - 1].date});
    }
    for (const p of placed) {
      const s = sessions[p.i];
      ses.push({date: p.date, loc: wi, titles: s.titles, anchors: s.anchors,
                y0: Math.min(...p.bundle) + top, y1: Math.max(...p.bundle) + top, n: p.members.length});
    }
    const ds = sortStr(placed.map(p => p.date));
    let ly = Infinity;
    for (const p of placed) for (const v of p.pos.values()) if (v < ly) ly = v;
    locations.push({loc: wi, lx: ds[0], ly: ly + top, n_people: lay.nPeople, n_sessions: placed.length,
                    from: ds[0], to: ds[ds.length - 1], crossings: lay.crossAfter, cross_before: lay.crossBefore,
                    n_aligned: lay.nAligned, compact_iters: lay.compactIters,
                    examples: placed.slice(0, 3).flatMap(p => sessions[p.i].titles).slice(0, 3)});
    top += lay.height + BAND_PAD;
  });
  const allds = sortStr(sessions.map(s => s.date));
  const credited = rated.filter(r => r.people && r.people.length && hasDate(r));
  const allPeople = new Set();
  for (const r of credited) for (const [, b] of r.people) allPeople.add(b);
  const worlds = locations.slice().sort((a, b) => a.loc - b.loc);
  const mx = sortStr(ses.map(s => s.date)).pop();
  const cut = isoOf(ordinal(mx) - 365);
  for (const wd of worlds) wd.recent = ses.filter(x => x.loc === wd.loc && cmp(x.date, cut) >= 0).length;
  return {lines, sessions: ses, worlds, height: top - BAND_PAD, from: allds[0], to: allds[allds.length - 1],
          min_times: minTimes, n_lines: keep.size, n_people_all: allPeople.size,
          n_dated: rated.filter(hasDate).length, n_credited: credited.length};
}

function recentLine(worlds) {
  const act = worlds.filter(w => w.recent);
  if (!act.length) return '';
  if (act.length === 1) {
    const w = act[0];
    return `<b>直近 1 年に束があるのは ${w.loc + 1} つめだけで、`
      + `${w.recent} 回です。</b>ほかの流れの公演は、この 1 年は観ていらっしゃいません。`;
  }
  let top = act[0];
  for (const w of act) if (w.recent > top.recent) top = w;
  const parts = act.map(w => `${w.loc + 1} つめが ${w.recent} 回`).join('、');
  return `<b>直近 1 年は${parts}です。</b>`
    + `いまは ${top.loc + 1} つめを多く観ています。`;
}

/** charts._table */
function chTable(head, rows) {
  const th = head.map(h => `<th>${E(h)}</th>`).join('');
  const tr = rows.map(r => '<tr>' + r.map(c => `<td>${E(c)}</td>`).join('') + '</tr>').join('');
  return `<details class="tv"><summary>数字で見る</summary>`
    + `<table class="tbl mini"><thead><tr>${th}</tr></thead><tbody>${tr}</tbody></table></details>`;
}

/** storyline.panel */
export function panel(rated, minTimes = MIN_TIMES) {
  const d = build(rated, minTimes);
  if (!d.worlds || !d.worlds.length) return '';
  const ws = d.worlds;
  const tbl = chTable(
    ['いくつめの世界', '人数', '観に行った回数', 'はじめ', 'おわり', '作品の例'],
    ws.map(w => [`${w.loc + 1} つめ`, `${w.n_people} 人`, `${w.n_sessions} 回`,
                 w.from, w.to, w.examples.map(t => slice(t, 0, 18)).join('、')]));
  const [xs, width] = xmap(d.sessions.map(x => x.date));
  const ticks = [], seenY = new Set();
  for (const dt of sortStr([...xs.keys()])) {
    const yr = slice(dt, 0, 4);
    if (!seenY.has(yr)) { seenY.add(yr); ticks.push({x: f(xs.get(dt)), label: yr + ' 年'}); }
  }
  const X = new Map([...xs].map(([k, v]) => [k, f(v)]));
  const lines = d.lines.map(l => ({...l, pts: new Pts(l.pts)}));
  const wsOut = ws.map(w => ({...w, ly: f(w.ly)}));
  const sesOut = d.sessions.map(s => ({...s, y0: f(s.y0), y1: f(s.y1)}));
  const payload = jd({lines, worlds: wsOut, sessions: sesOut, height: f(d.height),
                      from: d.from, to: d.to, runPx: f(RUN_PX), X, width: f(width), ticks, rowHref: ROW_HREF})
    // <script> の中に置くので「<」を逃がす（名前や題名に「</script>」があっても、そこで閉じない。people.js の scriptSafe と同じ）
    .replace(/</g, '\\u003c');
  return `<div class="card wide">${h2('light', 'Storyline')}
<p class="lead"><b>1 本の線が 1 人、横が時間です。同じ作品に出た方の線はその日に束になります。</b>
<b>● が「その日その作品に出ていた」印です。</b>束 1 つが 1 公演で、押すとその記録へ移動します。<br>
<b>線の色は ${ws.length} つに分かれています。</b>
${ws.map(w => `${w.n_people} 人（${w.from} 〜 ${w.to}）`).join('、')}で、
<b>この ${ws.length} つのあいだで一緒に出た方は 1 人もいません。</b>
${recentLine(ws)}<br>
線にしているのは <b>${minTimes} 回以上観た ${d.n_lines} 名</b>です。
作り手が分かっている ${d.n_credited} 件の記録には、のべ ${d.n_people_all} 名が出てきます。
横に引っぱると時間を伸ばせます（スマホでは指 2 本で広げます。指 1 本では図を送れます）。<b>線を押すと、その人の流れだけが浮き上がります。</b>
何人でも選べます。背景を押すと戻ります。</p>
<div class="sl-legend">${ws.map(w =>
    `<span class="sl-k sl-w${w.loc}">${w.loc + 1} つめの世界 ── `
    + `${w.n_people} 人・${w.n_sessions} 回</span>`).join('')}
 <span class="sl-hint">（${d.from} 〜 ${d.to}）</span></div>
<div id="sl" class="sl"></div>
<p class="sl-fallback">${tbl}</p>
</div>
<script id="sl-data" type="application/json">${payload}</script>` + `<script>${STORYLINE_JS}</script>`;
}
