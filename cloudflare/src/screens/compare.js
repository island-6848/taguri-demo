// 眺める の「比べる」: tools/taguri/compare.py の pop_note（比べる相手は何か）と
// panel（作りの型）。test/compare.test.js が Python の出力と 1 文字ずつ比べる。
//
// 材料は D1 から取る。比べる相手は rec_stage の今の版（CoRich のこれからの公演）、
// 「もう 1 つの一覧」は catalogue（劇場名と日付だけの一覧）。作りの型は、Python が
// クレジットの欄（fields の 翻訳・作曲・原作・振付）で見ていたのを、同じ欄から読んだ
// 役職（credits の役職名）で見る ── 公開の版に残っているのは役職と名前の組だけである。
// 「題材の偏り」は出さない: 題材のまとまり（theme_groups.json）が D1 に無く、Python も
// 訪問者の記録では数えられない（自分の側が 0 件になる）。
import {E, fmtF, sortBy} from './py.js';

const MIN_MINE = 2;
export const CRAFTS = [['翻訳', '翻訳劇（翻訳者がクレジットされている）'], ['作曲', '音楽劇（作曲者がクレジットされている）'],
  ['原作', '原作つき（原作がクレジットされている）'], ['振付', '振付つき（振付師がクレジットされている）']];

/** compare._rows */
export function rows(names, mine, world, nMine, nWorld) {
  if (!nMine || !nWorld) return [];
  const out = names.map(nm => {
    const a = mine[nm] || 0, b = world[nm] || 0, pa = a / nMine * 100, pb = b / nWorld * 100;
    return {label: nm, mine: pa, pop: pb, n: a, n_pop: b, ratio: pb ? pa / pb : null, thin: a < MIN_MINE};
  });
  return sortBy(out, r => [r.ratio === null, -(r.ratio || 0)]);
}

/** compare._table */
function table(rs, head, unit) {
  const mx = Math.max(...rs.map(r => Math.abs(r.mine - r.pop))) || 1;
  const body = rs.map(r => {
    const d = r.mine - r.pop, w = Math.abs(d) / mx * 50;
    const [cls, left] = d >= 0 ? ['pos', 50.0] : ['neg', 50.0 - w];
    let ratio;
    if (r.ratio === null) ratio = '<span class="dim">比べる相手なし</span>';
    else if (r.thin) ratio = `<span class="dim">${fmtF(r.ratio, 1)} 倍（${r.n} 件）</span>`;
    else if (Math.abs(r.ratio - 1) < 0.05) ratio = `<span class="dim">${fmtF(r.ratio, 1)} 倍（同じ割合）</span>`;
    else ratio = `<span class="${d >= 0 ? 'up' : 'dn'}">${fmtF(r.ratio, 1)} 倍</span>`;
    return `<tr><td class="nm">${E(r.label)}</td>`
      + `<td class="dv"><span class="axis"></span>`
      + `<span class="dvbar ${cls}" style="left:${fmtF(left, 1)}%;width:${fmtF(w, 1)}%"></span></td>`
      + `<td class="num">${fmtF(r.pop, 0)}%</td>`
      + `<td class="num strong">${fmtF(r.mine, 0)}%</td>`
      + `<td class="num">${ratio}</td>`
      + `<td class="num dim">${r.n}</td></tr>`;
  }).join('');
  return `<p class="compare-scroll-hint note">表は左右にスクロールできます。</p><div class="compare-table" role="region" aria-label="${E(head)}の比較表" tabindex="0"><table class="tbl"><thead><tr><th>${E(head)}</th>`
    + `<th class="th-dv">これからの公演との差</th><th class="num">これからの公演</th>`
    + `<th class="num">自分</th><th class="num">倍率</th>`
    + `<th class="num">${E(unit)}</th></tr></thead>`
    + `<tbody>${body}</tbody></table></div>`;
}

const LEGEND = '<div class="legend"><span class="lg"><i class="sw s-pos"></i>'
  + '自分のほうが多い</span>'
  + '<span class="lg"><i class="sw s-neg"></i>これからの公演のほうが多い</span>'
  + '<span class="lg">中心線＝同じ割合</span></div>';

/** compare.panel with the rows already counted: {craft: [rows, nMine, nWorld]} (the theme axis is not ported). */
export function panel({craft}) {
  const out = [];
  const [ks, km, kw] = craft || [[], 0, 0];
  if (ks.length) {
    out.push(`<section class="card">
<h2>作りの型 ── 翻訳劇・音楽劇をどれだけ観ているか</h2>
<p class="why"><b>公演ページのクレジットに、その欄があるかどうかで数えています。</b>
翻訳者の名前が載っていれば翻訳劇、作曲者が載っていれば音楽劇です。
あらすじからの推測はしていません。</p>
${LEGEND}
${table(ks, '作りの型', '作品')}
<p class="note">あなたの側はクレジットの取れた <b>${km} 作品</b>、比べる相手は
<b>${kw} 件</b>です。<b>${MIN_MINE} 件に満たない行は薄く表示しています。</b>
件数が少ないと、倍率が大きく振れるためです。
実際には翻訳劇でも、クレジットに欄が無い公演は数えられていません。</p>
</section>`);
  }
  return out.join('');
}

/** compare.pop_note with population() already counted (`first`/`last` are YYYY-MM-DD or null). */
export function popNote(rated, d) {
  if (!d.n) return '';
  const ds = rated.map(r => r.date).filter(Boolean).sort();
  const ym = s => `${s.slice(0, 4)} 年 ${Number(s.slice(5, 7))} 月`;
  const span = ds.length ? `あなたの記録は <b>${ym(ds[0])}から${ym(ds[ds.length - 1])}まで</b>の分で、` : '';
  const Y = s => Number(s.slice(0, 4)), M = s => Number(s.slice(5, 7));
  const months = !d.first ? 0 : Math.max(1, (Y(d.last) - Y(d.first)) * 12 + M(d.last) - M(d.first));
  const per = !d.first ? '' : `（初日が ${Y(d.first)} 年 ${M(d.first)} 月〜${Y(d.last)} 年 ${M(d.last)} 月）`;
  return `<section class="card">
<h2>比べる相手は何か</h2>
<p class="why"><b>比べる相手は演劇の情報サイト CoRich に載っている
「これから上演される公演」${d.n} 件です</b>${per}。
内訳は、初日前が ${d.n_upcoming} 件、上演中が ${d.n_running} 件、
最近終わった分が ${d.n_ended} 件です。</p>
<p class="note"><b>日本の演劇すべてではありません。</b>そのサイトに載っていない公演は
入りません。<br>
<b>時期がずれています。</b>${span}比べる相手は先の <b>${months} か月</b>ぶんの公演なので、
<b>過去のあなたの記録と、これからの公演を並べている</b>ことになります。<br>
手元にはもう 1 つ公演の一覧（${d.other} 件）がありますが、劇場名と日付しか無いので、
出演者や題材を使う図では数えていません。<br>
<b>図ごとに件数が違います。</b>あらすじや出演者が取れた分だけを数えているので、
件数はそれぞれの図に書いてあります。</p></section>`;
}

/**
 * compare.population and the world side of craft_rows, from D1. They scan the whole
 * catalogue version (thousands of rows read), so the answer is kept in rec_meta for the
 * version and the day: one count and one write a day, however many people open 眺める.
 */
export async function population(db, today) {
  const ver = (await db.prepare("SELECT v FROM rec_meta WHERE k='current'").first())?.v;
  if (!ver) return {n: 0, crafts: {}};
  const stamp = `${ver}|${today}`;
  const kept = await db.prepare("SELECT v FROM rec_meta WHERE k='compare_pop'").first();
  if (kept) { try { const p = JSON.parse(kept.v); if (p.stamp === stamp) return p; } catch { /* count again */ } }
  const s = await db.prepare(`SELECT count(*) n, sum(start<>'' AND start>?1) up, sum(start<>'' AND start<=?1 AND end>=?1) run,
    sum(start<>'' AND end<>'' AND end<?1) ended, min(nullif(start,'')) first, max(nullif(start,'')) last
    FROM rec_stage WHERE ver=?2`).bind(today, ver).first();
  const crafts = {};
  const {results} = await db.prepare(`SELECT role, count(DISTINCT stage_id) n FROM rec_credit WHERE ver=?1 AND role IN (${CRAFTS.map(() => '?').join(',')}) GROUP BY role`)
    .bind(ver, ...CRAFTS.map(c => c[0])).all();
  for (const r of results) crafts[r.role] = r.n;
  const other = (await db.prepare('SELECT count(*) n FROM catalogue').first())?.n || 0;
  const p = {stamp, n: s?.n || 0, n_upcoming: s?.up || 0, n_running: s?.run || 0, n_ended: s?.ended || 0,
    first: s?.first || null, last: s?.last || null, other, crafts};
  await db.prepare("INSERT INTO rec_meta(k,v) VALUES('compare_pop',?) ON CONFLICT(k) DO UPDATE SET v=excluded.v").bind(JSON.stringify(p)).run();
  return p;
}

/** compare.craft_rows: the rated rows whose credits are known against the catalogue version. */
export function craftRows(rated, pop) {
  const mf = rated.filter(r => (r.people || []).length);
  const mine = {}, world = {};
  for (const [key, lab] of CRAFTS) {
    mine[lab] = mf.filter(r => r.people.some(([role]) => role === key)).length;
    world[lab] = (pop.crafts || {})[key] || 0;
  }
  return [rows(CRAFTS.map(c => c[1]), mine, world, mf.length, pop.n), mf.length, pop.n];
}
