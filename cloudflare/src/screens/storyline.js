// 記録を見返す ▸ 同じ作品で一緒だった人の流れ: tools/taguri/storyline.py's panel() ported to
// the Worker. storyline.test.js checks panel() against storyline.panel byte for byte.
//
// Python behaviour copied on purpose:
// - sum() of floats is Neumaier-compensated since Python 3.12 (pySum below), so the layout's
//   heights come out to the same bits.
// - json.dumps prints a float that happens to be whole as "3.0"; floats in the payload are
//   wrapped in F so jd() can tell them from ints.
// - compact()'s neighbour list only ever holds the frames at t-1 and t+1 (frames are indexed by
//   t), so it reads those two directly instead of scanning every frame (same values, same order).
import {E, pyFloat, cmp, sortBy, slice} from './py.js';
import {h2} from './icons.js';
import {anchor} from './row.js';
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
/** json.dumps(x, ensure_ascii=False) with F for floats. */
function jd(x) {
  if (x instanceof F) return pyFloat(x.v);
  if (x === null || x === undefined) return 'null';
  if (x === true) return 'true';
  if (x === false) return 'false';
  if (typeof x === 'number') return Number.isInteger(x) ? String(x) : pyFloat(x);
  if (typeof x === 'string') return JSON.stringify(x);
  if (Array.isArray(x)) return '[' + x.map(jd).join(', ') + ']';
  if (x instanceof Map) return '{' + [...x].map(([k, v]) => JSON.stringify(k) + ': ' + jd(v)).join(', ') + '}';
  return '{' + Object.entries(x).map(([k, v]) => JSON.stringify(k) + ': ' + jd(v)).join(', ') + '}';
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

const sortStr = xs => xs.slice().sort(cmp);

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
  for (const r of sortBy(dated, x => x.date)) {
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
  const sets = sessions.map(s => new Set(s.members));
  for (let i = 0; i < sessions.length; i++) {
    for (let j = i + 1; j < sessions.length; j++) {
      if (sessions[j].members.some(m => sets[i].has(m))) par[find(i)] = find(j);
    }
  }
  const g = new Map();
  for (let i = 0; i < sessions.length; i++) {
    const r = find(i);
    if (!g.has(r)) g.set(r, []);
    g.get(r).push(i);
  }
  return sortBy([...g.values()], idx => [-idx.length, sessions[idx[0]].date]);
}

// ---------------------------------------------------------------- StoryFlow の 3 段
function framesOf(sessions, world) {
  const idx = sortBy(world, i => sessions[i].date);
  const first = new Map(), last = new Map();
  idx.forEach((i, t) => {
    for (const m of sessions[i].members) { if (!first.has(m)) first.set(m, t); last.set(m, t); }
  });
  return idx.map((i, t) => {
    const members = new Set(sessions[i].members);
    const live = [...first.keys()].filter(m => first.get(m) <= t && t <= last.get(m));
    return {i, t, date: sessions[i].date, members: sortStr([...members]), memberSet: members,
            live: sortStr(live), transit: sortStr(live.filter(m => !members.has(m)))};
  });
}

const rankOf = xs => { const r = new Map(); xs.forEach((m, k) => r.set(m, k)); return r; };

function countCrossings(frames, order) {
  let n = 0;
  for (let k = 0; k + 1 < frames.length; k++) {
    const ra = rankOf(order[frames[k].t]), rb = rankOf(order[frames[k + 1].t]);
    const both = [...ra.keys()].filter(m => rb.has(m));
    const pa = both.map(m => ra.get(m)), pb = both.map(m => rb.get(m));
    for (let x = 0; x < both.length; x++) {
      for (let y = x + 1; y < both.length; y++) if ((pa[x] - pa[y]) * (pb[x] - pb[y]) < 0) n++;
    }
  }
  return n;
}

function pairCrossings(ref, cur, ra = rankOf(ref)) {
  const both = [];
  for (const m of cur) if (ra.has(m)) both.push(ra.get(m));
  let n = 0;
  for (let i = 0; i < both.length; i++) for (let j = i + 1; j < both.length; j++) if (both[i] > both[j]) n++;
  return n;
}

function reorder(frame, ref) {
  const rank = rankOf(ref);
  const blk = sortBy(frame.members, m => [rank.has(m) ? rank.get(m) : Infinity, m]);
  const out = frame.transit.filter(m => rank.has(m));
  out.sort((a, b) => rank.get(a) - rank.get(b));
  out.push(...sortStr(frame.transit.filter(m => !rank.has(m))));
  // Python builds every out[:k] + blk + out[k:] and counts its crossings. Only the pairs
  // (outside line, bundle line) change with k, so count those incrementally: moving out[k]
  // from after the bundle to before it trades its "above" pairs for its "below" pairs.
  // Same counts, same first minimum, without the O(k·n²) rebuild.
  const R = blk.filter(m => rank.has(m)).map(m => rank.get(m));
  const below = [], above = [];
  for (const m of out) {
    let lo = 0, hi = 0;
    if (rank.has(m)) { const r = rank.get(m); for (const b of R) { if (b < r) lo++; else if (b > r) hi++; } }
    below.push(lo); above.push(hi);
  }
  let n = 0;
  for (const v of above) n += v;
  let bestK = 0, bestN = n;
  for (let k = 0; k < out.length; k++) {
    n += below[k] - above[k];
    if (n < bestN) { bestN = n; bestK = k + 1; }
  }
  return out.slice(0, bestK).concat(blk, out.slice(bestK));
}

function orderSweep(frames) {
  const order = {};
  for (const fr of frames) order[fr.t] = fr.members.concat(fr.transit);
  const copy = () => { const o = {}; for (const fr of frames) o[fr.t] = order[fr.t].slice(); return o; };
  const first = countCrossings(frames, order);
  let best = copy(), bestN = first;
  const sweep = seq => {
    for (let k = 1; k < seq.length; k++) {
      const ref = order[seq[k - 1].t], fr = seq[k];
      const cand = reorder(fr, ref);
      const ra = rankOf(ref);
      if (pairCrossings(ref, cand, ra) < pairCrossings(ref, order[fr.t], ra)) order[fr.t] = cand;
    }
  };
  const rev = frames.slice().reverse();
  for (let k = 0; k < SWEEPS; k++) {
    sweep(k % 2 === 0 ? frames : rev);
    const n = countCrossings(frames, order);
    if (n < bestN) { bestN = n; best = copy(); }
    if (bestN === 0) break;
  }
  return [best, bestN, first];
}

function alignFrames(frames, order) {
  const out = [];
  for (let k = 0; k + 1 < frames.length; k++) {
    const a = frames[k], b = frames[k + 1];
    const both = sortStr(a.members.filter(m => b.memberSet.has(m)));
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

function gapsOf(frame, o) {
  const mem = frame.memberSet, g = new Array(Math.max(o.length - 1, 0));
  for (let k = 0; k + 1 < o.length; k++) g[k] = mem.has(o[k]) && mem.has(o[k + 1]) ? D_IN : D_OUT;
  return g;
}

function project(want, gaps) {
  const n = want.length, cum = new Array(gaps.length + 1);
  let acc = 0.0;
  cum[0] = 0.0;
  for (let k = 0; k < gaps.length; k++) { acc += gaps[k]; cum[k + 1] = acc; }
  const sv = [], sw = [];
  for (let k = 0; k < n; k++) {
    sv.push(want[k] - cum[k]); sw.push(1.0);
    while (sv.length > 1 && sv[sv.length - 2] > sv[sv.length - 1] - 1e-12) {
      const v2 = sv.pop(), w2 = sw.pop(), v1 = sv.pop(), w1 = sw.pop();
      sv.push((v1 * w1 + v2 * w2) / (w1 + w2)); sw.push(w1 + w2);
    }
  }
  const out = new Array(n);
  let k = 0;
  for (let s = 0; s < sv.length; s++) {
    const c = Math.round(sw[s]);        // the weights are whole numbers, no tie to break
    for (let j = 0; j < c; j++, k++) out[k] = sv[s] + cum[k];
  }
  return out;
}

function compact(frames, order, aligns) {
  const y = {};                           // t -> Map(name -> height)
  for (const fr of frames) {
    const o = order[fr.t], g = gapsOf(fr, o);
    const pos = [0.0];
    let acc = 0.0;
    for (const gg of g) { acc += gg; pos.push(acc); }
    const mid = pySum(pos) / pos.length;
    y[fr.t] = new Map(o.map((m, k) => [m, pos[k] - mid]));
  }
  // (5b): the anchors that pin a line at frame b to its height at frame a (dict order).
  const pins = {};
  for (const [a, b, m] of aligns) (pins[b] = pins[b] || []).push([a, m]);
  const gapsAt = {}, pinAt = {};
  for (const fr of frames) {
    const o = order[fr.t];
    gapsAt[fr.t] = gapsOf(fr, o);
    pinAt[fr.t] = (pins[fr.t] || []).filter(([, m]) => o.includes(m)).map(([a, m]) => [a, m, o.indexOf(m)]);
  }
  let it = 0;
  for (it = 1; it <= 600; it++) {
    let moved = 0.0;
    for (const fr of frames) {
      const t = fr.t, o = order[t], yt = y[t];
      const prev = y[t - 1], next = y[t + 1];
      const want = new Array(o.length);
      for (let k = 0; k < o.length; k++) {
        const m = o[k];
        const nb = [];
        if (prev && prev.has(m)) nb.push(prev.get(m));
        if (next && next.has(m)) nb.push(next.get(m));
        want[k] = nb.length ? pySum(nb) / (nb.length + BETA) : 0.0;
      }
      for (const [a, m, k] of pinAt[t]) want[k] = y[a].get(m);
      const nw = project(want, gapsAt[t]);
      for (let k = 0; k < o.length; k++) {
        const d = Math.abs(nw[k] - yt.get(o[k]));
        if (d > moved) moved = d;
        yt.set(o[k], nw[k]);
      }
    }
    if (moved < 1e-4) break;
  }
  if (it > 600) it = 600;
  hold(frames, order, y, gapsAt);
  return [y, it];
}

function hold(frames, order, y, gapsAt, rounds = 12) {
  const seq = new Map();
  for (const fr of frames) for (const m of order[fr.t]) { if (!seq.has(m)) seq.set(m, []); seq.get(m).push(fr.t); }
  for (let r = 0; r < rounds; r++) {
    let changed = false;
    for (const [m, ts] of seq) {
      for (let k = 0; k + 1 < ts.length; k++) {
        const a = ts[k], b = ts[k + 1];
        const d = y[b].get(m) - y[a].get(m);
        if (Math.abs(d) > 0.0 && Math.abs(d) < SNAP) { y[b].set(m, y[a].get(m)); changed = true; }
      }
    }
    for (const fr of frames) {
      const o = order[fr.t], yt = y[fr.t];
      const fixed = project(o.map(m => yt.get(m)), gapsAt[fr.t]);
      o.forEach((m, k) => yt.set(m, fixed[k]));
    }
    if (!changed) break;
  }
}

function layout(sessions, world) {
  const frames = framesOf(sessions, world);
  const [order, nCross, nFirst] = orderSweep(frames);
  const aligns = alignFrames(frames, order);
  const [y, nIter] = compact(frames, order, aligns);
  let lo = Infinity;
  for (const fr of frames) for (const v of y[fr.t].values()) if (v < lo) lo = v;
  const placed = [];
  for (const fr of frames) {
    const pos = new Map(order[fr.t].map(m => [m, y[fr.t].get(m) - lo]));
    placed.push({i: fr.i, t: fr.t, date: fr.date, members: fr.members, memberSet: fr.memberSet,
                 transit: fr.transit, order: order[fr.t], pos,
                 bundle: fr.members.map(m => pos.get(m))});
  }
  let hi = -Infinity;
  for (const p of placed) for (const v of p.pos.values()) if (v > hi) hi = v;
  const people = new Set();
  for (const p of placed) for (const m of p.pos.keys()) people.add(m);
  return {placed, height: hi - lo, nPeople: people.size,
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
      const pts = sortBy(per.get(m), x => x.date);
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
  const worlds = sortBy(locations, x => x.loc);
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
      + `${w.recent} 回です。</b>ほかの流れは、この 1 年は観ていらっしゃいません。`;
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
  const lines = d.lines.map(l => ({...l, pts: l.pts.map(p => ({date: p.date, y: f(p.y), on: p.on}))}));
  const wsOut = ws.map(w => ({...w, ly: f(w.ly)}));
  const sesOut = d.sessions.map(s => ({...s, y0: f(s.y0), y1: f(s.y1)}));
  const payload = jd({lines, worlds: wsOut, sessions: sesOut, height: f(d.height),
                      from: d.from, to: d.to, runPx: f(RUN_PX), X, width: f(width), ticks, rowHref: ROW_HREF});
  return `<div class="card wide">${h2('light', '同じ作品で一緒だった人の流れ')}
<p class="lead"><b>1 本の線が 1 人、横が時間です。同じ作品に出た方の線は、その日に束になります。</b>
<b>● が「その日その作品に出ていた」印です。</b>束が 1 つの公演で、押すとその記録へ移動します。<br>
<b>線の色は ${ws.length} つに分かれています。</b>
${ws.map(w => `${w.n_people} 人（${w.from} 〜 ${w.to}）`).join('、')}で、
<b>この ${ws.length} つのあいだで一緒に出た方は 1 人もいません。</b>
${recentLine(ws)}<br>
線にしているのは <b>${minTimes} 回以上観た ${d.n_lines} 名</b>です
（作り手が分かっている ${d.n_credited} 件の記録には、のべ ${d.n_people_all} 名が出てきます）。
横に引っぱると時間を伸ばせます。<b>線を押すと、その人の流れだけが浮き上がります。</b>
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
