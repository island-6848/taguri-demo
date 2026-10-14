// 眺める の図のうち、手元の記録だけで描ける 2 枚: tools/taguri/charts.py の
// venue_panel（よく行く劇場）と spiral_panel（観劇の年輪）。test/charts.test.js が
// Python の出力と 1 文字ずつ比べる。
//
// map_panel（行った劇場の地図）は移していない: 劇場の座標（venue_geo.json）と
// 地図の輪郭が D1 に無い。Python も座標が無ければ空を返すので、同じく出さない。
import {STARS, isStar, gradeText, markOf} from './grade.js';
import {E, fmtF, sortBy} from './py.js';
import {h2} from './icons.js';
import {anchor} from './anchor.js';

export const ROW_HREF = '/records/works?t=__TAGURI_TOKEN__';
const VERDICT_FILL = {'◎': 'var(--pos)', '○': 'var(--pos)', '△': 'var(--neg)', '×': 'var(--neg)'};
const VERDICT_OP = {'◎': 1.0, '○': 0.42, '△': 0.42, '×': 1.0};
const VERDICT_ORDER = ['◎', '○', '△', '×', 'まだ判断できない'];
const opStr = x => (Number.isInteger(x) ? x.toFixed(1) : String(x));   // str(float)

/** charts._table */
export function table(head, rows) {
  const th = head.map(h => `<th>${E(h)}</th>`).join('');
  const tr = rows.map(r => '<tr>' + r.map(c => `<td>${E(c)}</td>`).join('') + '</tr>').join('');
  return `<details class="tv"><summary>数字で見る</summary>`
    + `<table class="tbl mini"><thead><tr>${th}</tr></thead><tbody>${tr}</tbody></table></details>`;
}

/** collections.Counter: counts in first-seen order; mostCommon is Python's stable order. */
class Counter extends Map {
  add(k, n = 1) { this.set(k, (this.get(k) || 0) + n); }
  mostCommon(n) { const all = sortBy([...this.entries()], kv => -kv[1]); return n === undefined ? all : all.slice(0, n); }
}

function venueBlock(cnt, top, unit, note) {
  const rows = cnt.mostCommon(top);
  if (!rows.length) return '';
  const mx = rows[0][1];
  const bars = rows.map(([name, v]) => `<div class="hb" title="${E(name)} ── ${v} ${unit}">`
    + `<span class="hb-l">${E(name)}</span>`
    + `<span class="hb-t"><span class="hb-f" style="width:${fmtF(v / mx * 100, 1)}%"></span></span>`
    + `<span class="hb-v">${v}</span></div>`).join('');
  return `<div class="vsub">${unit}で数える <span class="badge part">上位 ${rows.length} 館</span></div>
<p class="lead">${note}</p>
<div class="hbars">${bars}</div>
${table(['劇場', unit], rows.map(([n, v]) => [n, v]))}`;
}

const squash = name => String(name || '').normalize('NFKC').replace(/[ 　・･\-‐‑‒–—―−]/gu, '');

/** charts.venue_panel */
export function venuePanel(rated, top = 10, showsByKey = {}) {
  const cntWork = new Counter();
  for (const r of rated) for (const v of r.venues || []) cntWork.add(v);
  if (!cntWork.size) return '';
  const cntShow = new Counter();
  for (const r of rated) {
    const venues = r.venues || [];
    const shows = venues.length > 1 ? showsByKey[r.key] : null;
    if (!shows || !shows.length) {
      for (const v of venues) cntShow.add(v, r.times || 1);
      continue;
    }
    const bySquash = new Map(venues.map(v => [squash(v), v]));
    for (const s of shows) cntShow.add(bySquash.get(squash(s)) ?? s);
  }
  const work = venueBlock(cntWork, top, '本', '同じ公演を何度も観ても、1 本として数えます。');
  const show = venueBlock(cntShow, top, '公演', '同じ公演を複数回観た場合は、その都度数えます。実際に足を運んだ回数です。');
  return `<section class="card wide">
${h2('building', 'よく行く劇場')}
<p class="lead">作り手の分かっている ${rated.length} 作品をもとに、劇場ごとに数えています。
評価は入れていません。</p>
<div class="vcols"><div class="vcol">${work}</div><div class="vcol">${show}</div></div></section>`;
}

/** charts._polar: 12 o'clock is 1 January, clockwise. */
function polar(day, ring, cx, cy) {
  const a = 2 * Math.PI * (day / 366.0) - 2 * Math.PI / 4;
  return [cx + ring * Math.cos(a), cy + ring * Math.sin(a)];
}

const yday = iso => {
  const t = Date.UTC(+iso.slice(0, 4), +iso.slice(5, 7) - 1, +iso.slice(8, 10));
  return Math.round((t - Date.UTC(+iso.slice(0, 4), 0, 1)) / 864e5) + 1;
};

/** charts.spiral_panel */
export function spiralPanel(works) {
  const rows = works.filter(w => /^\d{4}$/.test((w.first_date || '').slice(0, 4)));
  if (!rows.length) return '';
  const years = [...new Set(rows.map(w => w.first_date.slice(0, 4)))].sort();
  const r0 = 38.0, dr = Math.max(Math.min(156.0 / Math.max(years.length, 1), 30.0), 16.0);
  const R = r0 + dr * (years.length - 1);
  const size = (R + 34) * 2;
  const cx = size / 2, cy = size / 2;
  const f1 = x => fmtF(x, 1);

  const spokes = [], mlabs = [];
  for (let m = 0; m < 12; m++) {
    const d0 = Math.trunc(m * 30.5) + 1;
    const [ix, iy] = polar(d0, r0 - 7, cx, cy);
    const [ox, oy] = polar(d0, R + 5, cx, cy);
    spokes.push(`<line x1="${f1(ix)}" y1="${f1(iy)}" x2="${f1(ox)}" y2="${f1(oy)}"/>`);
    const [lx, ly] = polar(Math.trunc(m * 30.5) + 16, R + 20, cx, cy);
    mlabs.push(`<text class="mo" x="${f1(lx)}" y="${f1(ly)}">${m + 1}</text>`);
  }
  const rings = [], ylabs = [];
  years.forEach((y, i) => {
    const rr = r0 + dr * i;
    rings.push(`<circle cx="${f1(cx)}" cy="${f1(cy)}" r="${f1(rr)}"/>`);
    ylabs.push(`<text class="yr" x="${f1(cx)}" y="${f1(cy - rr)}">${E(y)}</text>`);
  });

  const pts = [], tally = new Counter();
  for (const w of sortBy(rows, w => w.first_date)) {
    const rr = r0 + dr * years.indexOf(w.first_date.slice(0, 4));
    const [x, y] = polar(yday(w.first_date), rr, cx, cy);
    const v = w.verdict || '';
    const m = markOf(v);       // a star is coloured as the mark on its side (★3: neither)
    tally.add(isStar(v) ? gradeText(v) : v in VERDICT_FILL ? v : '未評価');
    const fill = VERDICT_FILL[m] || 'var(--unk)';
    const solid = m === '◎' || m === '○';
    const times = (w.times || 1) > 1 ? `・${w.times} 回` : '';
    const a = E(anchor(w.work_key));
    pts.push(`<a href="${ROW_HREF}&amp;w=${a}#w-${a}"><g class="pt">`
      + `<title>${E(w.title)} ── ${E(w.first_date)}${E(times)}${v ? '・' + E(gradeText(v)) : '・評価なし'}</title>`
      + `<circle cx="${f1(x)}" cy="${f1(y)}" r="5"`
      + ` fill="${solid ? fill : 'var(--surf)'}"`
      + ` fill-opacity="${solid ? opStr(VERDICT_OP[m] ?? 1.0) : 1}"`
      + ` stroke="${fill}" stroke-width="${solid ? 1.6 : 2}"/></g></a>`);
  }
  const leg = [...VERDICT_ORDER.slice(0, 4), ...STARS.map(gradeText), '未評価'].filter(g => tally.get(g)).map(label => {
    const g = label.startsWith('★') ? markOf(label.slice(1) + '/5') : label;
    const solid = g === '◎' || g === '○';
    return `<span class="lg"><svg width="13" height="13" viewBox="0 0 13 13" aria-hidden="true">`
      + `<circle cx="6.5" cy="6.5" r="5" fill="${solid ? (VERDICT_FILL[g] || 'var(--unk)') : 'var(--surf)'}"`
      + ` fill-opacity="${solid ? opStr(VERDICT_OP[g] ?? 1.0) : 1}"`
      + ` stroke="${VERDICT_FILL[g] || 'var(--base)'}" stroke-width="2"/></svg>`
      + `${E(label)} <b>${tally.get(label)}</b></span>`;
  }).join('');

  const grid = new Counter();
  for (const w of rows) grid.add(`${w.first_date.slice(0, 4)}|${w.first_date.slice(5, 7)}`);
  const head = ['年', ...Array.from({length: 12}, (_, i) => `${i + 1}月`), '計'];
  const trows = years.map(y => [y, ...Array.from({length: 12}, (_, i) => grid.get(`${y}|${String(i + 1).padStart(2, '0')}`) ?? ''),
    rows.filter(w => w.first_date.slice(0, 4) === y).length]);
  const mon = new Counter();
  for (const w of rows) mon.add(w.first_date.slice(5, 7));
  const peak = mon.mostCommon(1)[0];
  let thin = null;
  if (mon.size === 12) for (const kv of mon) if (!thin || kv[1] < thin[1]) thin = kv;
  const sz = fmtF(size, 0);
  return `<section class="card">
${h2('chart', '観劇の年輪 ── 毎年いつ観ているか', `<span class="badge part">${rows.length} 公演・${years.length} 年</span>`)}
<p class="lead"><b>1 つの点が 1 公演です。</b>時計と同じ向きに月が進み、
<b>内側が ${E(years[0])} 年、外側が ${E(years[years.length - 1])} 年</b>です。
同じ方角に点が縦に並んでいれば、その月に毎年観ているということです。
いちばん多いのは <b>${Number(peak[0])} 月の ${peak[1]} 公演</b>
${thin ? `、いちばん少ないのは ${Number(thin[0])} 月の ${thin[1]} 公演` : ''}です。
<b>点を押すと、下のその公演の記録に飛びます。</b></p>
<div class="ring"><svg viewBox="0 0 ${sz} ${sz}" width="100%"
 style="max-width:${sz}px" role="img"
 aria-label="観劇の年輪。角度が月、半径が年で、1 点が 1 公演">
<g class="sp">${spokes.join('')}</g><g class="rg">${rings.join('')}</g>
${mlabs.join('')}${pts.join('')}
${ylabs.join('')}</svg></div>
<div class="legend">${leg}</div>
${table(head, trows)}</section>`;
}
