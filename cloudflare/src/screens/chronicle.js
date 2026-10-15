// 記録を見返す ▸ 観劇史年表: chronicle.panel for a public user (owner=False: the facts and
// the figure, no LLM reading) ported to the Worker (起案者の指示 2026-10-14「残りの画面も
// 順に移して」). chronicle.test.js checks it against chronicle.panel on the same records.
// The subject and tone words of the works seen (themes.jsonl, rated side) are the owner's
// batch output, so `themes` is empty here (as in Python without that file).
import {isTop, isScaled, gradeText} from './grade.js';
import {E, fmtF} from './py.js';
import {h2} from './icons.js';
import {anchor} from './row.js';
import {CHRONICLE_JS} from './calendar_js.js';

const ROLES = ['出演', '演出', '作', '脚本', '翻訳', '原作', '演出補', '振付', '作曲'];
const ROW_HREF = '/records/works?t=__TAGURI_TOKEN__';
const LANES = 10, LANE_MIN = 2, LH = 25, GUT = 176, FW = 900, TOP = 38;
const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
const f1 = x => fmtF(x, 1), f0 = x => fmtF(x, 0);

/** A collections.Counter: insertion-ordered counts. */
class Counter extends Map {
  add(k, n = 1) { this.set(k, (this.get(k) || 0) + n); }
  mostCommon(k = Infinity) { return [...this].sort((a, b) => b[1] - a[1]).slice(0, k); }
}
const sumOf = c => [...c.values()].reduce((s, n) => s + n, 0);
const timesOf = w => Number(w.times || 1);

/** chronicle.facts (no themes) */
export function facts(works, rated) {
  const rr = new Map(rated.map(r => [r.key, r]));
  const dated = works.filter(w => /^\d{4}/.test((w.first_date || '').slice(0, 4)) && w.bucket !== 'upcoming')
    .sort((a, b) => cmp(a.first_date, b.first_date));
  const byYear = new Map();
  for (const w of dated) { const y = w.first_date.slice(0, 4); if (!byYear.has(y)) byYear.set(y, []); byYear.get(y).push(w); }
  const seenV = new Set(), firstYear = new Map(), pplYears = new Map(), pplN = new Counter(), venYears = new Map();
  const key = (r, n) => r + '\u0000' + n;
  const years = [];
  for (const y of [...byYear.keys()].sort()) {
    const g = byYear.get(y);
    const ven = new Counter(), ppl = new Counter();
    const loved = new Set();
    for (const w of g) {
      const r = rr.get(w.work_key) || {};
      for (const v of r.venues || []) { ven.add(v); if (!venYears.has(v)) venYears.set(v, new Set()); venYears.get(v).add(y); }
      for (const pair of r.people || []) {
        const [role, name] = [...pair, '', ''].slice(0, 2);
        if (!ROLES.includes(role)) continue;
        const k = key(role, name);
        ppl.add(k);
        if (!pplYears.has(k)) pplYears.set(k, new Set());
        pplYears.get(k).add(y);
        pplN.add(k);
        if (isTop(w.verdict)) loved.add(name);
      }
    }
    const newV = [...ven.keys()].filter(v => !seenV.has(v));
    for (const v of ven.keys()) seenV.add(v);
    const byName = new Map();
    for (const [k, n] of ppl) {
      const [role, nm] = k.split('\u0000');
      if (!byName.has(nm)) byName.set(nm, new Counter());
      byName.get(nm).add(role, n);
    }
    const ranked = [...byName].sort((a, b) => sumOf(b[1]) - sumOf(a[1]));
    const newP = ranked.filter(([nm, c]) => loved.has(nm) && [...c.keys()].every(r => !firstYear.has(key(r, nm))));
    for (const k of ppl.keys()) if (!firstYear.has(k)) firstYear.set(k, y);
    const desc = c => c.mostCommon().map(([r, n]) => `${r} ${n}`).join('・');
    years.push({
      year: y, works: g.length, times: g.reduce((s, w) => s + timesOf(w), 0),
      venues: ven.mostCommon(4), new_venues: newV.slice(0, 5),
      people: ranked.slice(0, 5).map(([nm, c]) => [nm, desc(c), sumOf(c)]),
      new_people: newP.map(([nm, c]) => [nm, desc(c), sumOf(c)]).slice(0, 4),
      themes: [], tone: [],
      loved: g.filter(w => isTop(w.verdict)).map(w => w.title).slice(0, 6),
      repeats: g.filter(w => timesOf(w) > 1).map(w => [w.title, timesOf(w)]).sort((a, b) => b[1] - a[1]).slice(0, 5),
    });
  }
  const ys = years.map(x => x.year);
  const links = new Map(dated.map(w => [w.title, w.work_key || '']));
  const marks = dated.map(w => ({d: w.first_date, t: w.title, k: w.work_key || '', v: ((rr.get(w.work_key) || {}).venues || [''])[0], verdict: w.verdict || '', times: timesOf(w)}));
  const keepV = [...venYears].filter(([, s]) => s.size >= 3).map(([v, s]) => [v, [...s].sort()])
    .sort((a, b) => (b[1].length - a[1].length) || cmp(a[0], b[0])).slice(0, 6);
  const longP = [...pplYears].filter(([k, s]) => s.size >= 2 && pplN.get(k) >= 3)
    .map(([k, s]) => { const [role, nm] = k.split('\u0000'); return [role, nm, [...s].sort(), pplN.get(k)]; })
    .sort((a, b) => (b[3] - a[3]) || cmp(a[1], b[1])).slice(0, 8);
  void ys;
  return {links, marks, years, kept_venues: keepV.map(([v, s]) => [v, s[0], s.at(-1), s.length]),
    long_people: longP.map(([role, nm, s, n]) => [role, nm, s[0], s.at(-1), n]), n_works: dated.length,
    n_undated: works.filter(w => !/^\d{4}/.test((w.first_date || '').slice(0, 4)) && w.bucket !== 'upcoming').length};
}

const ym = d => Number(d.slice(0, 4)) * 12 + Number(d.slice(5, 7)) - 1;
const cut = (title, n = 34) => (Array.from(title).length <= n ? title : Array.from(title).slice(0, n).join('') + '…');
/** charts._table */
const table = (head, rows) => `<details class="tv"><summary>数字で見る</summary><table class="tbl mini"><thead><tr>${head.map(h => `<th>${E(h)}</th>`).join('')}</tr></thead>`
  + `<tbody>${rows.map(r => '<tr>' + r.map(c => `<td>${E(c)}</td>`).join('') + '</tr>').join('')}</tbody></table></details>`;

/** chronicle._figure (no reading: no era bands) */
function figure(f) {
  const marks = f.marks.filter(m => m.d);
  if (marks.length < 3) return '';
  const lo = Math.min(...marks.map(m => ym(m.d))), hi = Math.max(...marks.map(m => ym(m.d)));
  const span = Math.max(hi - lo, 1), plot = FW - GUT - 14;
  const x = v => GUT + (v - lo) / span * plot;
  const cx = v => Math.min(Math.max(x(v), GUT), FW - 14);
  const cnt = new Counter(), first = new Map();
  for (const m of marks) if (m.v) { cnt.add(m.v); if (!first.has(m.v)) first.set(m.v, ym(m.d)); }
  const qual = [...cnt].filter(([, n]) => n >= LANE_MIN).map(([v]) => v);
  const keep = [...qual].sort((a, b) => (cnt.get(b) - cnt.get(a)) || (first.get(a) - first.get(b))).slice(0, Math.max(LANES - 3, 1));
  const late = qual.filter(v => !keep.includes(v)).sort((a, b) => first.get(b) - first.get(a)).slice(0, Math.max(LANES - keep.length, 0));
  const big = [...keep, ...late].sort((a, b) => first.get(a) - first.get(b));
  const rest = marks.filter(m => m.v && !big.includes(m.v)), none = marks.filter(m => !m.v);
  const lanes = [...big];
  if (rest.length) lanes.push(`1 回だけ行った劇場（${new Set(rest.map(m => m.v)).size} 館）`);
  if (none.length) lanes.push('劇場が記録に無い公演');
  const row = new Map(lanes.map((v, i) => [v, i]));
  const fall = rest.length ? lanes[big.length] : (none.length ? lanes.at(-1) : '');
  const h = TOP + lanes.length * LH + 26;
  const grid = [];
  for (let y = Math.floor(lo / 12); y <= Math.floor(hi / 12); y++) {
    const gx = cx(y * 12), edge = x(y * 12) < GUT;
    grid.push((edge ? '' : `<line class="gl" x1="${f1(gx)}" y1="${f0(TOP - 16)}" x2="${f1(gx)}" y2="${f0(TOP + lanes.length * LH)}"/>`)
      + `<text class="ylab${edge ? ' st' : ''}" x="${f1(gx)}" y="${f0(h - 8)}">${y}</text>`);
  }
  const rowsSvg = lanes.map(v => {
    const cy = TOP + row.get(v) * LH + LH / 2;
    return `<line class="lane" x1="${GUT}" y1="${f1(cy)}" x2="${FW - 14}" y2="${f1(cy)}"/>`
      + `<text class="vlab2" x="${GUT - 10}" y="${f1(cy + 4)}"><title>${E(v)}</title>${E(cut(v, 15))}</text>`;
  });
  const laneOf = m => (row.has(m.v) ? m.v : (!m.v && none.length ? '劇場が記録に無い公演' : fall));
  const dots = [];
  for (const m of marks) {
    const v = laneOf(m);
    if (!row.has(v)) continue;
    const cy = TOP + row.get(v) * LH + LH / 2, px = x(ym(m.d));
    const say = `${m.t} ── ${m.d}` + (m.times > 1 ? `・${m.times} 回` : '') + (m.verdict ? `・${gradeText(m.verdict)}` : '');
    const a = m.k ? anchor(m.k) : '';
    const dot = `<circle class="dot${isTop(m.verdict) ? ' on' : ''}" cx="${f1(px)}" cy="${f1(cy)}" r="4.5"><title>${E(say)}</title></circle>`;
    dots.push(a ? `<a href="${ROW_HREF}&amp;w=${E(a)}#w-${E(a)}">${dot}</a>` : dot);
  }
  const nLane = big.reduce((s, v) => s + cnt.get(v), 0);
  const yrs = Array.from({length: Math.floor(hi / 12) - Math.floor(lo / 12) + 1}, (_, i) => Math.floor(lo / 12) + i);
  const tbl = lanes.map(v => {
    const got = marks.filter(m => laneOf(m) === v);
    const per = new Counter();
    for (const m of got) per.add(m.d.slice(0, 4));
    return [v, ...yrs.map(y => per.get(String(y)) ?? ''), got.length];
  });
  return `<div class="chfig"><svg viewBox="0 0 ${FW} ${h}" width="100%" role="img" aria-label="観劇の年表。横が時間、1 本の行が 1 つの劇場、1 点が 1 作品">`
    + `${grid.join('')}${rowsSvg.join('')}${dots.join('')}</svg></div>`
    + '<div class="legend chleg"><span class="lg"><svg width="13" height="13" viewBox="0 0 13 13" aria-hidden="true"><circle class="dot on" cx="6.5" cy="6.5" r="4.5"/></svg>' + topOf(marks) + ' を付けた作品</span>'
    + '<span class="lg"><svg width="13" height="13" viewBox="0 0 13 13" aria-hidden="true"><circle class="dot" cx="6.5" cy="6.5" r="4.5"/></svg>そのほかの作品</span>'
    + '<span class="lgn">行は劇場です。<b>初めて行った順</b>に上から並べていますので、<b>行の始まりと終わりが、通い始めた時期と途切れた時期です。</b>'
    + `${LANE_MIN} 回以上行った ${big.length} 館（${nLane} 作品）を 1 行ずつにし、1 回だけの劇場は下に 1 行でまとめています。</span></div>`
    + table(['劇場', ...yrs.map(y => `${y} 年`), '計'], tbl);
}

const roles = rs => rs.split('・').slice(0, 2).map(x => `${x} 本`).join('・');
function workLink(title, links) {
  const k = links.get(title) || '';
  if (!k) return E(cut(title));
  const a = anchor(k);
  return `<a href="${ROW_HREF}&amp;w=${E(a)}#w-${E(a)}" title="${E(title)}">${E(cut(title))}</a>`;
}
/** The top grade's name in these records (★5 for a star user). */
const topOf = ms => { const t = ms.find(m => isScaled(m.verdict) && isTop(m.verdict)); return t ? gradeText(t.verdict) : '◎'; };
function chips(y, links, top = '◎') {
  const out = [];
  if (y.new_venues.length) out.push(`<li><b>初めて行った劇場</b>${E(y.new_venues.slice(0, 3).join('／'))}</li>`);
  if (y.new_people.length) out.push('<li><b>この年に出会った作り手</b>' + E(y.new_people.slice(0, 3).map(([nm, rs]) => `${nm}（${roles(rs)}）`).join('／')) + '</li>');
  if (y.repeats.length) out.push('<li><b>くり返し観た作品</b>' + y.repeats.slice(0, 3).map(([t, n]) => `${workLink(t, links)}（${n} 回）`).join('／') + '</li>');
  if (y.loved.length) out.push(`<li><b>${top} を付けた作品</b>` + y.loved.slice(0, 3).map(t => workLink(t, links)).join('／') + (y.loved.length > 3 ? `　ほか ${y.loved.length - 3} 本` : '') + '</li>');
  return out.length ? `<ul class="chfacts">${out.join('')}</ul>` : '';
}

/** chronicle.panel(works, rated, owner=False) */
export function panel(works, rated) {
  const f = facts(works, rated);
  if (!f.years.length) return '';
  const rows = f.years.map(y => {
    const top = y.venues.length && y.venues[0][1] >= 2 ? y.venues[0][0] : '';
    return `<div class="chyear"><div class="chy"><b>${E(y.year)}</b><i>${y.works} 作品・のべ ${y.times} 回</i></div>`
      + `<div class="chbody">${top ? `<p class='chtop'>いちばん通った劇場は${E(top)}です。</p>` : ''}${chips(y, f.links, topOf(f.marks))}</div></div>`;
  }).join('');
  const kept = f.kept_venues.slice(0, 3).map(([v, a, b, n]) => `${v}（${a}〜${b} 年に ${n} 年）`).join('／');
  const longP = f.long_people.slice(0, 3).map(([role, nm, a, b, n]) => `${nm}（${role}・${a}〜${b} 年に ${n} 本）`).join('／');
  const across = kept || longP ? '<div class="chacross"><h3>年をまたいで続いているもの</h3><ul>'
    + (kept ? `<li><b>通い続けている劇場</b>${E(kept)}</li>` : '') + (longP ? `<li><b>何年も観ている作り手</b>${E(longP)}</li>` : '') + '</ul></div>' : '';
  const undated = f.n_undated ? `<p class="chnote">公演日が記録に無い ${f.n_undated} 件は、年に置けないのでこの年表には出していません。「日記帳」には残っています。</p>` : '';
  return `<section class="card chcard wide">
${h2('book', '観劇の年表', `<span class="badge part">${f.n_works} 作品</span>`)}
<p class="lead">記録を年の順に並べ、<b>その年に何が始まったか</b>を出しています。
本数だけでは同じに見える年でも、通う劇場と観る作り手は入れ替わっています。
<b>図の 1 点が 1 作品です。点を押すと、その公演の記録に飛びます。</b></p>

${figure(f)}
${rows}${across}
<div class="chfoot"><span class="said"></span></div>
${undated}</section>${CHRONICLE_JS}`;
}
