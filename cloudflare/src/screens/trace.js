// 記録を見返す ▸ たどる: tools/taguri/trace.py ported to the Worker (起案者の指示 2026-10-14
// 「残りの画面も順に移して」). trace.test.js checks body() against trace.body on the same
// rated rows. The rows are measure_nets.load_rated for a public user (records.ratedRows).
import {E, quote, fmtF} from './py.js';
import {ico, h2} from './icons.js';
import {anchor} from './row.js';
import {md5hex} from './md5.js';
import {nz} from './lists.js';

export const KEEP_ROLES = ['出演', '演出', '脚本', '作', '原作', '翻訳', '音楽', '作曲', '振付'];
const MIN_WORKS = 2, BRANCH_MIN = 3, BRANCH_MAX = 4, BRANCH_AWAY = 180, TRAIL_MAX = 3;
const HREF = '/records/trace?t=__TAGURI_TOKEN__';
const ROW_HREF = '/records/works?t=__TAGURI_TOKEN__';
const ARROW = '→';
const SVG_W = 880.0, MID_Y = 150.0, PAD_X = 52.0, GAP_MIN = 74.0;
const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
const f1 = x => fmtF(x, 1);

/** collections.Counter.most_common(k): count desc, ties in first-seen order. */
const mostCommon = (counter, k) => [...counter].sort((a, b) => b[1] - a[1]).slice(0, k).map(([name]) => name);
const ordinal = s => { const t = Date.parse(s + 'T00:00:00Z'); return Number.isNaN(t) ? null : Math.round(t / 86400000); };
function days(a, b) { const x = ordinal(a), y = ordinal(b); return x === null || y === null ? 0 : y - x; }

/** trace.build */
export function build(rated) {
  const dated = rated.filter(r => r.date).sort((a, b) => cmp(a.date, b.date) || cmp(a.key || '', b.key || ''));
  const occ = new Map(), roles = new Map(), who = new Map();
  for (const r of dated) {
    const ps = new Set();
    for (const [role, person] of r.people || []) {
      if (!KEEP_ROLES.includes(role)) continue;
      if (!roles.has(person)) roles.set(person, new Map());
      roles.get(person).set(role, (roles.get(person).get(role) || 0) + 1);
      if (!occ.has(person)) occ.set(person, new Map());
      occ.get(person).set(r.key, r);
      ps.add(person);
    }
    who.set(r.key, ps);
  }
  const first = new Map();
  for (const r of dated) for (const p of who.get(r.key) || []) if (!first.has(p)) first.set(p, r.key);
  const threads = new Map();
  for (const [p, v] of occ) if (v.size >= MIN_WORKS) threads.set(p, [...v.values()].sort((a, b) => cmp(a.date, b.date)));
  return {threads, roles, who, first, occ, n_all: rated.length, n_dated: dated.length, n_undated: rated.length - dated.length, declared: null};
}

const declaredNames = g => g.declared || new Set();
/** trace.picks */
function picks(g) {
  const dec = declaredNames(g);
  const out = [...g.threads].map(([name, rows]) => ({name, role: mostCommon(g.roles.get(name), 2).join('・'), n: rows.length,
    from: rows[0].date, to: rows.at(-1).date, span: days(rows[0].date, rows.at(-1).date), declared: dec.has(nz(name))}));
  return out.sort((a, b) => (a.declared - b.declared) || (b.span - a.span) || (b.n - a.n) || cmp(a.name, b.name));
}
const leaves = (g, person, date) => [...(g.occ.get(person) || new Map()).values()].some(r => Math.abs(days(date, r.date)) > BRANCH_AWAY);
/** trace.branches */
function branches(g, name) {
  const rows = g.threads.get(name) || [];
  const out = new Map(), used = new Set([name]);
  for (const r of rows) {
    const cand = [...(g.who.get(r.key) || [])].filter(p => !used.has(p) && (g.occ.get(p)?.size || 0) >= BRANCH_MIN && leaves(g, p, r.date));
    if (!cand.length) continue;
    cand.sort((p, q) => ((g.first.get(p) !== r.key) - (g.first.get(q) !== r.key)) || (g.occ.get(q).size - g.occ.get(p).size) || cmp(p, q));
    for (const p of cand) used.add(p);
    out.set(r.key, cand.map(p => ({name: p, n: g.occ.get(p).size, new: g.first.get(p) === r.key, role: mostCommon(g.roles.get(p), 2).join('・')})));
  }
  return out;
}

const wob = (seed, lo, hi) => lo + (hi - lo) * (parseInt(md5hex(seed).slice(0, 8), 16) % 1000) / 999.0;
function xsOf(rows) {
  const ds = [];
  for (const r of rows) { const o = ordinal(r.date); ds.push(o === null ? (ds.length ? ds.at(-1) : 0) : o); }
  const lo = Math.min(...ds), hi = Math.max(...ds), span = SVG_W - PAD_X * 2;
  let xs = ds.map((d, i) => PAD_X + (hi > lo ? span * (d - lo) / (hi - lo) : span * i / Math.max(ds.length - 1, 1)));
  for (let i = 1; i < xs.length; i++) xs[i] = Math.max(xs[i], xs[i - 1] + GAP_MIN);
  if (xs.at(-1) > SVG_W - PAD_X) { const k = (SVG_W - PAD_X * 2) / (xs.at(-1) - xs[0]); const x0 = xs[0]; xs = xs.map(x => PAD_X + (x - x0) * k); }
  return xs;
}
const jdate = s => { const m = /^(\d+)-(\d+)-(\d+)$/.exec(s || ''); return m ? `${Number(m[1])}年${Number(m[2])}月${Number(m[3])}日` : (s || ''); };
const q = s => quote(s);

function threadSvg(name, rows, brs, nxt) {
  const xs = xsOf(rows);
  const ys = rows.map((_, i) => MID_Y + wob(`${name}#${i}#y`, -5.0, 5.0));
  const segs = [], hi = [];
  for (let i = 0; i < rows.length - 1; i++) {
    const [x0, y0, x1, y1] = [xs[i], ys[i], xs[i + 1], ys[i + 1]];
    const sag = wob(`${name}#${i}#s`, 7.0, 17.0);
    const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2 + sag;
    const w = wob(`${name}#${i}#w`, 4.6, 6.2);
    const d = `M${f1(x0)} ${f1(y0)}Q${f1(cx)} ${f1(cy)} ${f1(x1)} ${f1(y1)}`;
    segs.push(`<path d="${d}" class="ln" stroke-width="${f1(w)}"/>`);
    segs.push(`<path d="${d}" class="ln2" stroke-width="${f1(w * .3)}" transform="translate(0,-1.1)"/>`);
    hi.push(`<path d="${d}" class="ln3" stroke-width="${f1(w * .26)}" transform="translate(0,1.2)"/>`);
  }
  const knots = [], labs = [], brh = [];
  let maxStack = 0;
  const ROW_H = 17.5, LABEL_W = 230.0;
  rows.forEach((r, i) => {
    const x = xs[i], y = ys[i], a = anchor(r.key);
    const rr = 7.2 + wob(`${name}#${i}#r`, -0.9, 1.3);
    knots.push(`<a href="${ROW_HREF}&amp;w=${E(a)}#w-${E(a)}"><g class="kn"><title>${E(r.title)} ── ${E(jdate(r.date))}</title>`
      + `<circle cx="${f1(x)}" cy="${f1(y)}" r="${f1(rr + 2.6)}" class="kh"/><circle cx="${f1(x)}" cy="${f1(y)}" r="${f1(rr)}" class="kc"/>`
      + `<text x="${f1(x)}" y="${f1(y + 3.6)}" class="kn-n">${i + 1}</text></g></a>`);
    labs.push(`<text x="${f1(x)}" y="${f1(y - 20)}" class="kd">${E(r.date.slice(0, 4))}<tspan class="kd2">.${E(r.date.slice(5, 7))}</tspan></text>`);
    const bs = brs.get(r.key);
    if (!bs || brh.length >= BRANCH_MAX) return;
    const flip = x + 30 + LABEL_W > SVG_W - PAD_X;
    const bx = flip ? x - 30 : x + 30, by0 = y + 74;
    maxStack = Math.max(maxStack, bs.length);
    const parts = [`<path d="M${f1(x)} ${f1(y)}Q${f1(x)} ${f1(y + 46)} ${f1(bx)} ${f1(by0)}" class="br"/>`];
    bs.forEach((b, j) => {
      const by = by0 + j * ROW_H;
      if (j) parts.push(`<path d="M${f1(bx)} ${f1(by - ROW_H)}V${f1(by)}" class="br"/>`);
      const tx = flip ? bx - 11 : bx + 11;
      parts.push(`<a href="${nxt}${E(q(b.name))}"><g class="bn"><circle cx="${f1(bx)}" cy="${f1(by)}" r="5.4" class="kc"/>`
        + `<text x="${f1(tx)}" y="${f1(by + 4.2)}" class="bl"${flip ? ' text-anchor="end"' : ''}>`
        + `${E(b.name)}<tspan class="bl2"> ${b.n} 作品${b.new ? '・はじめて' : ''}</tspan></text></g></a>`);
    });
    brh.push(parts.join(''));
  });
  const h = MID_Y + (brh.length ? 74 + maxStack * ROW_H + 24 : 62);
  return `<div class="thr"><svg viewBox="0 0 ${fmtF(SVG_W, 0)} ${fmtF(h, 0)}" width="100%" style="max-width:${fmtF(SVG_W, 0)}px" role="img" aria-label="`
    + `${E(name)}が関わった公演を、観た日の順に線で結んだ図。結び目 1 つが 1 公演">`
    + `<g class="pull">${segs.join('')}${hi.join('')}${brh.join('')}${labs.join('')}${knots.join('')}</g></svg></div>`;
}

function pickPanel(g) {
  const ps = picks(g);
  if (!ps.length) return '<section class="card"><p class="empty">2 つ以上の公演で観た名前がまだありません。観た記録が増えると出るようになります。</p></section>';
  const rows = ps.map(p => `<li><a href="${HREF}&amp;name=${E(q(p.name))}" class="pk"><span class="pk-n">${E(p.name)}</span>`
    + `<span class="pk-r">${E(p.role)}</span><span class="pk-c">${p.n} 作品</span>`
    + `<span class="pk-s">${E(jdate(p.from))} 〜 ${E(jdate(p.to))}</span>${p.declared ? '<span class="pk-d">お気に入りに登録済み</span>' : ''}</a></li>`).join('');
  const nDec = ps.filter(p => p.declared).length;
  return `<section class="card">
${h2('light', 'どの名前をたどりますか', `<span class="badge part">${ps.length} 名</span>`)}
<p class="lead"><b>2 つ以上の公演で観た名前です。</b>お気に入りに登録していない名前を先に、
そのなかで<b>最初に観た日から最後に観た日までが長い順</b>に並べています。
登録済みの ${nDec} 名はすでにご存じの名前なので後ろにしています。</p>
<div class="pk-search">${ico('search', 15)}
<input type="text" data-pk-filter="1" placeholder="名前で絞り込む" autocomplete="off"
 aria-label="たどる名前を絞り込む"></div>
<ol class="picks">${rows}</ol>
<p class="empty pk-none" hidden>その名前は見つかりませんでした。</p></section>`;
}

function threadPanel(g, name, trail) {
  const rows = g.threads.get(name);
  if (!rows) return `<section class="card"><p class="empty"><b>${E(name)}</b>の記録には、上演日のあるものが 2 件そろっていません。この線は 2 件目から引けます。</p></section>`;
  const brs = branches(g, name);
  const nxt = `${HREF}&amp;via=${E(q([...trail, name].slice(-TRAIL_MAX).join(ARROW)))}&amp;name=`;
  const dec = declaredNames(g).has(nz(name)) ? '（お気に入りに登録済みです）' : '';
  const role = mostCommon(g.roles.get(name), 3).join('・');
  const lis = rows.map((r, i) => {
    const a = anchor(r.key), ven = (r.venues || [])[0];
    const bs = brs.get(r.key) || [];
    const links = bs.map(b => `<a href="${nxt}${E(q(b.name))}">${E(b.name)}</a>（${E(b.role)}・${b.n} 作品${b.new ? '・この公演がはじめて' : ''}）`).join('、');
    const bh = bs.length ? `<p class="brl">この公演から移れる名前：${links}</p>` : '';
    return `<li><span class="no">${i + 1}</span><div><a href="${ROW_HREF}&amp;w=${E(a)}#w-${E(a)}" class="ti">${E(r.title)}</a>`
      + `<p class="me">${E(jdate(r.date))}${ven ? '　' + E(ven) : ''}</p>${bh}</div></li>`;
  }).join('');
  return `<section class="card">
${h2('light', `${name} ── ${rows.length} 作品`, `<span class="badge part">${jdate(rows[0].date)} 〜 ${jdate(rows.at(-1).date)}</span>`)}
<p class="lead"><b>${E(role)}</b>として観た公演を、古いほうから順に結んでいます${E(dec)}。
<b>結び目 1 つが 1 公演です。</b>押すと日記帳のその記録に飛びます。
${brs.size ? '下に垂れている名前を押すと、その名前に移ります。その公演ではじめて観た名前には、その旨を書いています。' : 'この線からは、次の名前に移れる公演がありませんでした。'}</p>
${threadSvg(name, rows, brs, nxt)}
<ol class="knots">${lis}</ol></section>`;
}

function trailHtml(trail, name) {
  if (!trail.length) return '';
  const ks = [...trail, name].slice(-(TRAIL_MAX + 1));
  const parts = ks.map((k, i) => (i === ks.length - 1 ? `<b>${E(k)}</b>`
    : `<a href="${HREF}&amp;via=${E(q(ks.slice(0, i).join(ARROW)))}&amp;name=${E(q(k))}">${E(k)}</a>`)).join(' → ');
  return `<p class="trail">たどってきた道　${parts}</p>`;
}

/** trace.body; declared: kind -> names (the user's お気に入り). */
export function body(rated, name = '', via = '', declared = null) {
  const g = build(rated);
  if (declared) g.declared = new Set(Object.values(declared).flat().map(nz));
  const trail = String(via || '').split(ARROW).filter(t => t.trim()).slice(-TRAIL_MAX);
  const und = !g.n_undated ? '' : `<p class="lead"><b>上演日が分からない記録が ${g.n_undated} 件あります。</b>この線には載りません。日記帳の「公演詳細を直す」から日付を入れると載るようになります。</p>`;
  const main = name ? threadPanel(g, name, trail) : pickPanel(g);
  const back = name ? `<p class="lead"><a href="${HREF}" class="back">ほかの名前を選ぶ</a></p>` : '';
  return `${name ? trailHtml(trail, name) : ''}${main}${und}${back}`;
}
