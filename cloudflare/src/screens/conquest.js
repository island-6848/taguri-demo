// 劇場制覇マップ ── 都道府県ごとに、行った劇場がその県の劇場のうちいくつか（起案者の指示 2026-10-16
// 「同じ建物の別ホールは分けたほうがいいな。…組み込んで」、mock-theater-conquest）。
// 地図は形ではなくタイル（1 県 1 マス、McNeill & Hale 2017〔lit-tilemap-mcneill2017〕）。県の形は D1 に無く、
// 東京のような小さい県ほど行った劇場が多いので、同じ大きさのマスのほうが読める。
// 分母は venue_census（migration 0027）: 取得した公演に 2 回以上出てきた会場。ホールはまとめない。
// 行った会場がその中に無くても（手で足した作品の劇場など）、行った劇場として数え、その県の分母にも足す。
import {E} from './py.js';
import {h2} from './icons.js';
import {PREFS} from './prefs.js';

// 列・行（0 始まり）。北海道を右上、沖縄を左下に置く
export const POS = {'北海道': [12, 0], '青森県': [12, 1], '秋田県': [11, 2], '岩手県': [12, 2], '石川県': [8, 3], '富山県': [9, 3],
  '新潟県': [10, 3], '山形県': [11, 3], '宮城県': [12, 3], '福井県': [8, 4], '岐阜県': [9, 4], '長野県': [10, 4], '群馬県': [11, 4],
  '福島県': [12, 4], '島根県': [4, 5], '鳥取県': [5, 5], '兵庫県': [6, 5], '京都府': [7, 5], '滋賀県': [8, 5], '愛知県': [9, 5],
  '山梨県': [10, 5], '埼玉県': [11, 5], '栃木県': [12, 5], '佐賀県': [1, 6], '福岡県': [2, 6], '山口県': [3, 6], '広島県': [4, 6],
  '岡山県': [5, 6], '大阪府': [6, 6], '奈良県': [7, 6], '三重県': [8, 6], '静岡県': [9, 6], '神奈川県': [10, 6], '東京都': [11, 6],
  '茨城県': [12, 6], '長崎県': [0, 7], '熊本県': [1, 7], '大分県': [2, 7], '愛媛県': [4, 7], '香川県': [5, 7], '徳島県': [6, 7],
  '和歌山県': [7, 7], '千葉県': [12, 7], '鹿児島県': [1, 8], '宮崎県': [2, 8], '高知県': [5, 8], '沖縄県': [0, 9]};
// 色の段（行った劇場の数 → 幕の色を混ぜる割合）。いちばん濃くても字が読める 56% まで
export const STEPS = [[1, 16, '1'], [2, 28, '2〜4'], [5, 42, '5〜9'], [10, 56, '10 以上']];
const PER_QUERY = 90;

/** The venue name as the census keys it (deliver_catalogue.venue_key): NFKC, no whitespace. */
export const venueKey = s => String(s || '').normalize('NFKC').replace(/\s+/g, '');
const short = p => (p === '北海道' ? p : p.replace(/[都府県]$/, ''));
const mix = pct => `color-mix(in srgb, var(--curtain) ${pct}%, var(--surf))`;
export function fill(k) {
  if (!k) return 'var(--plane)';
  let pct = STEPS[0][1];
  for (const [min, p] of STEPS) if (k >= min) pct = p;
  return mix(pct);
}

/**
 * Per prefecture: the venues visited and how many there are. `visited`: [{key, name, pref}] (one per
 * venue), `counts`: {pref: venues in the census} or null, `inCensus`: the keys found in the census.
 */
export function tally(visited, counts, inCensus) {
  const by = Object.fromEntries(PREFS.map(p => [p, {names: [], years: [], total: counts ? counts[p] || 0 : null}]));
  for (const v of visited) {
    const t = by[v.pref];
    if (!t) continue;
    t.names.push(v.name);
    t.years.push(v.year ?? null);
    if (t.total !== null && !inCensus.has(v.key)) t.total += 1;
  }
  for (const t of Object.values(by)) {
    const order = t.names.map((n, i) => i).sort((i, j) => t.names[i].localeCompare(t.names[j], 'ja'));
    t.names = order.map(i => t.names[i]);
    t.years = order.map(i => t.years[i]);
  }
  return by;
}

const W = 46, H = 40;

/** The panel. `by` from tally(); `unknown`: venues whose prefecture is not known. */
export function conquestPanel(by, unknown = []) {
  const n = p => by[p].names.length;
  const visited = PREFS.reduce((a, p) => a + n(p), 0);
  if (!visited && !unknown.length) return '';
  const prefs = PREFS.filter(p => n(p)).length;
  const known = PREFS.every(p => by[p].total !== null);
  const total = known ? PREFS.reduce((a, p) => a + by[p].total, 0) : null;
  const of = p => (known ? `${n(p)}/${by[p].total}` : String(n(p)));
  const tiles = PREFS.map(p => {
    const [c, r] = POS[p], x = c * W, y = r * H;
    const tip = known ? `${p}：${n(p)} / ${by[p].total} か所` : `${p}：${n(p)} か所`;
    return `<g class="cq-tile" data-p="${E(p)}"><title>${E(tip)}</title>`
      + `<rect x="${x + 1}" y="${y + 1}" width="${W - 2}" height="${H - 2}" rx="5" fill="${fill(n(p))}"/>`
      + `<text x="${x + W / 2}" y="${y + H * 0.45}">${E(short(p))}</text>`
      + `<text class="n" x="${x + W / 2}" y="${y + H * 0.8}">${E(of(p))}</text></g>`;
  }).join('');
  const legend = `<span><i class="cq-none"></i>まだ</span>`
    + STEPS.map(([, pct, t]) => `<span><i style="background:${mix(pct)}"></i>${E(t)} か所</span>`).join('');
  const list = PREFS.filter(p => n(p)).map(p => `<details><summary><b>${E(p)}</b>　${E(of(p))} か所</summary>`
    + `<ul>${by[p].names.map(v => `<li>${E(v)}</li>`).join('')}</ul></details>`).join('');
  const rest = unknown.length
    ? `<details><summary>都道府県が分からない劇場　${unknown.length} か所</summary><ul>${unknown.map(v => `<li>${E(v)}</li>`).join('')}</ul></details>`
    : '';
  // 時点で育つ地図: 年の目盛り（JS が無ければ出さない。web/app.js fixupConquest が塗り直す）
  const years = [...new Set(PREFS.flatMap(p => by[p].years).filter(y => y !== null))].sort((a, b) => a - b);
  const grow = years.length >= 2 ? {years, steps: STEPS.map(([min, pct]) => [min, pct]), known,
    v: PREFS.flatMap(p => by[p].names.map((name, i) => [p, by[p].years[i], name])),
    total: Object.fromEntries(PREFS.map(p => [p, by[p].total]))} : null;
  const slider = grow ? `<div class="cq-grow" hidden><label>いつまでに行ったか
<input type="range" min="0" max="${years.length}" value="${years.length}" step="1" aria-valuetext="今まで"></label>
<output>今まで</output><span class="cq-new">はじめて行った県は縁取り</span></div>` : '';
  const lead = `行った劇場 <b>${visited}</b>${total !== null ? `（全国 ${total.toLocaleString('ja-JP')} のうち）` : ''}・`
    + `行った都道府県 <b>${prefs} / 47</b>。マスの色は、その県で行った劇場の数です。`;
  return `<section class="card cq"${grow ? ` data-cq="${E(JSON.stringify(grow))}"` : ''}>
${h2('building', '劇場制覇マップ ── どこの劇場に行ったか', `<span class="badge part">${visited} か所</span>`)}
<p class="lead">${lead}</p>
${slider}
<div class="cq-map"><svg viewBox="0 0 ${13 * W} ${10 * H}" width="100%" style="max-width:${13 * W}px" role="img" aria-label="都道府県のタイル地図。色が行った劇場の数">${tiles}</svg></div>
<div class="cq-legend">${legend}</div>
<div class="cq-list">${list}${rest}</div>
<p class="fine">その県の劇場の数は、たぐりが集めた公演（これからの公演と 2019 年以降の過去の公演）に 2 回以上出てきた会場です。同じ建物の別のホールは別に数えます。そこに無い劇場に行っていたら、行った劇場として数え、その県の数にも足しています。</p>
</section>`;
}

async function inChunks(keys, run) {
  for (let i = 0; i < keys.length; i += PER_QUERY) await run(keys.slice(i, i + PER_QUERY));
}
const marks = n => Array(n).fill('?').join(',');

/**
 * The venues of the seen works: [{key, name, pref, year}] (pref '' when unknown), one per venue.
 * `year` is the first year the user went there (the earliest 観た日 of its works; null when no work has one).
 */
export async function visitedVenues(db, seen) {
  const sids = [...new Set(seen.map(w => w.stage_id).filter(Boolean).map(String))];
  const stage = {};
  await inChunks(sids, async part => {
    const {results} = await db.prepare(`SELECT stage_id, entry FROM rec_stage WHERE ver=(SELECT v FROM rec_meta WHERE k='current') AND stage_id IN (${marks(part.length)})`).bind(...part).all();
    for (const r of results) {
      try {
        const e = JSON.parse(r.entry || '{}');
        const name = e.theater || e.venue || (e.fields || {})['劇場'] || '';
        if (name) stage[r.stage_id] = {name, pref: e.pref || ''};
      } catch { /* no entry */ }
    }
  });
  await inChunks(sids.filter(s => !stage[s]), async part => {
    const {results} = await db.prepare(`SELECT stage_id, venue, pref FROM past_stage WHERE stage_id IN (${marks(part.length)})`).bind(...part).all();
    for (const r of results) if (r.venue) stage[r.stage_id] = {name: r.venue, pref: r.pref || ''};
  });
  const out = new Map();
  for (const w of seen) {
    const s = stage[w.stage_id] || (w.venue ? {name: w.venue, pref: ''} : null);
    const key = s && venueKey(s.name);
    if (!key) continue;
    const year = /^\d{4}/.test(w.first_date || '') ? +w.first_date.slice(0, 4) : null;
    const had = out.get(key);
    if (!had) out.set(key, {key, name: String(s.name).trim(), pref: s.pref, year});
    else {
      if (!had.pref && s.pref) had.pref = s.pref;
      if (year !== null && (had.year === null || year < had.year)) had.year = year;
    }
  }
  return [...out.values()];
}

/** The panel for the user ('' when no seen work has a venue). */
export async function conquestFor(ctx, seen) {
  const visited = await visitedVenues(ctx.db, seen);
  if (!visited.length) return '';
  const census = new Map();
  await inChunks(visited.map(v => v.key), async part => {
    const {results} = await ctx.db.prepare(`SELECT venue, pref FROM venue_census WHERE venue IN (${marks(part.length)})`).bind(...part).all();
    for (const r of results) census.set(r.venue, r.pref);
  });
  // 分母と同じ県で数える（取得した公演の多くが言う県）。分母に無ければ公演の県、それも無ければ劇場の県
  const noPref = visited.filter(v => !census.has(v.key) && !PREFS.includes(v.pref)).map(v => v.name);
  const vp = new Map();
  await inChunks(noPref, async part => {
    const {results} = await ctx.db.prepare(`SELECT venue, pref FROM venue_pref WHERE venue IN (${marks(part.length)})`).bind(...part).all();
    for (const r of results) vp.set(r.venue, r.pref);
  });
  for (const v of visited) v.pref = census.get(v.key) || (PREFS.includes(v.pref) ? v.pref : vp.get(v.name) || '');
  const row = await ctx.db.prepare("SELECT v FROM rec_meta WHERE k='venue_counts'").first();
  let counts = null;
  try { counts = row && row.v ? JSON.parse(row.v) : null; } catch { counts = null; }
  const by = tally(visited.filter(v => v.pref), counts, new Set(census.keys()));
  return conquestPanel(by, visited.filter(v => !v.pref).map(v => v.name).sort((a, b) => a.localeCompare(b, 'ja')));
}
