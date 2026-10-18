// 記録を見返す ▸ 観劇史年表: chronicle.panel ported to the Worker (起案者の指示 2026-10-14「残りの画面も
// 順に移して」): the facts, the figure, and the reading (eras, a line per year, the profile, the
// closing) written by the same rules as chronicle.reading, with no LLM call (起案者の指示 2026-10-18).
// chronicle.test.js checks the HTML and the reading against Python on the same records/facts.
// CPU: one pass over the works for the facts, then arithmetic over the years only.
// The subject and tone words of the works seen (themes.jsonl, rated side) are the owner's
// batch output, so `themes` is empty here (as in Python without that file).
import {isTop, isScaled, gradeText, markOf} from './grade.js';
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
      hard: g.filter(w => ['△', '×'].includes(markOf(w.verdict))).map(w => w.title).slice(0, 3),
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
  const leftV = [...venYears].filter(([, s]) => s.size >= 2 && ys.length && [...s].sort().at(-1) < ys.at(-1))
    .map(([v, s]) => [v, [...s].sort()]).sort((a, b) => cmp(a[1].at(-1), b[1].at(-1)) || (b[1].length - a[1].length)).slice(0, 6);
  const tally = {};
  for (const w of dated) if (w.verdict) tally[w.verdict] = (tally[w.verdict] || 0) + 1;
  return {links, marks, years, kept_venues: keepV.map(([v, s]) => [v, s[0], s.at(-1), s.length]),
    left_venues: leftV.map(([v, s]) => [v, s[0], s.at(-1)]),
    long_people: longP.map(([role, nm, s, n]) => [role, nm, s[0], s.at(-1), n]),
    overall_themes: [], overall_tone: [], verdict_tally: tally,
    n_repeated: dated.filter(w => timesOf(w) > 1).length, n_loved: dated.filter(w => isTop(w.verdict)).length,
    n_hard: dated.filter(w => ['△', '×'].includes(markOf(w.verdict))).length, n_works: dated.length,
    n_undated: works.filter(w => !/^\d{4}/.test((w.first_date || '').slice(0, 4)) && w.bucket !== 'upcoming').length};
}

// ---------------------------------------------------------------- 読み（規則）
// chronicle.reading and its helpers, rule for rule (起案者の指示 2026-10-18: no LLM per user).
// Only arithmetic over the yearly facts; lengths count code points like Python's len().
const YEAR_MAX = 70, ERA_MAX = 140, MAX_CUTS = 3;
const ulen = s => Array.from(s).length;
const and = xs => (xs.length <= 1 ? xs.join('') : xs.length === 2 ? `${xs[0]}と${xs[1]}` : xs.join('、'));
const topVenue = y => (y.venues.length && y.venues[0][1] >= 2 ? y.venues[0][0] : '');
const topWord = (rows, least = 1) => (rows.length && rows[0][1] >= least ? rows[0][0] : '');
const byDesc = (xs, f) => [...xs].sort((a, b) => f(b) - f(a));

function appearOf(f) {
  const out = new Map();
  for (const y of f.years) for (const [nm] of y.people) { if (!out.has(nm)) out.set(nm, []); out.get(nm).push(y.year); }
  return out;
}
const continued = (y, appear) => y.new_people.map(p => p[0]).filter(nm => (appear.get(nm) || []).some(yy => yy > y.year));

function turn(p, y, appear) {
  let s = 0;
  if (Number(y.year) - Number(p.year) >= 2) s++;
  const a = p.works, b = y.works;
  if ((b >= 2 * a || 2 * b <= a) && Math.abs(b - a) >= 2) s++;
  const tp = topVenue(p), ty = topVenue(y);
  if (tp && ty && tp !== ty) s++;
  const nv = y.new_venues.length;
  if (nv >= 2 && 2 * nv > y.venues.length) s++;
  if (continued(y, appear).length) s++;
  const hp = topWord(p.themes), hy = topWord(y.themes);
  if (hp && hy && hp !== hy) s++;
  if (y.repeats.length && y.repeats[0][1] >= 3 && !p.repeats.length) s++;
  return s;
}

function cutsOf(f, appear) {
  const ys = f.years, n = ys.length, score = new Map();
  for (let i = 1; i < n; i++) score.set(i, turn(ys[i - 1], ys[i], appear));
  const order = [...score.keys()].sort((i, j) => (score.get(j) - score.get(i)) || (i - j));
  const fits = (i, got) => n < 4 || (i >= 2 && n - i >= 2 && got.every(c => Math.abs(i - c) >= 2));
  let cuts = [];
  for (const i of order) if (score.get(i) >= 2 && cuts.length < MAX_CUTS && fits(i, cuts)) cuts.push(i);
  if (!cuts.length && n >= 3) cuts = order.filter(i => score.get(i) >= 1 && fits(i, [])).slice(0, 1);
  return cuts.sort((i, j) => i - j);
}

function sumEra(g) {
  const ven = new Counter(), th = new Counter(), newV = [], newP = [];
  let reps = [];
  for (const y of g) {
    for (const [v, n] of y.venues) ven.add(v, n);
    for (const [w, n] of y.themes) th.add(w, n);
    for (const v of y.new_venues) if (!newV.includes(v)) newV.push(v);
    for (const [nm] of y.new_people) if (!newP.includes(nm)) newP.push(nm);
    reps = reps.concat(y.repeats);
  }
  const top = byDesc([...ven], x => x[1]), tops = byDesc([...th], x => x[1]);
  return {from: g[0].year, to: g.at(-1).year, k: Number(g.at(-1).year) - Number(g[0].year) + 1,
    works: g.reduce((s, y) => s + y.works, 0), n: g.length,
    top: top.length && top[0][1] >= 2 ? top[0][0] : '', top_n: top.length ? top[0][1] : 0,
    theme: tops.length && tops[0][1] >= 2 ? tops[0][0] : '',
    new_venues: newV, new_people: newP, repeats: byDesc(reps, x => x[1])};
}

function eraName(s, i, last, prev) {
  const span = s.k === 1 ? '年' : ` ${s.k} 年`;
  if (s.top && 2 * s.top_n >= s.works) return last ? `${s.top}に通う${span}` : `${s.top}に通っていた${span}`;
  if (s.new_venues.length >= 3 && 2 * s.new_venues.length >= s.works) return `劇場を広げていった${span}`;
  if (s.new_people.length) return s.k === 1 ? `${s.new_people[0]}と出会った年` : `${s.new_people[0]}と出会ってからの${span}`;
  if (s.repeats.length && s.repeats[0][1] >= 3) return `同じ作品に通った${span}`;
  if (i === 0) return `観劇の記録が始まった${span}`;
  if (prev && s.works * prev.k > prev.works * s.k) return `観る本数が増えた${span}`;
  if (prev && s.works * prev.k < prev.works * s.k) return `本数を絞った${span}`;
  return `前の流れが続いた${span}`;
}

function eraBody(s, prev, nxt, f, appear) {
  const cand = [];
  const nv = s.new_venues;
  if (nv.length) cand.push([`この時期に初めて行った劇場は${and(nv.slice(0, 2))}${nv.length > 2 ? 'など' : ''}です。`, nv.slice(0, 2)]);
  if (prev && prev.top && s.top && prev.top !== s.top) cand.push([`通う先は${prev.top}から${s.top}へ移りました。`, [prev.top, s.top]]);
  else if (!prev && s.top) cand.push([`いちばん通ったのは${s.top}です。`, [s.top]]);
  if (s.theme) {
    if (prev && prev.theme && prev.theme !== s.theme) cand.push([`題材は${prev.theme}から${s.theme}へ移っています。`, [prev.theme, s.theme]]);
    else if (!prev || prev.theme !== s.theme) cand.push([`題材では${s.theme}が目立ちます。`, [s.theme]]);
  }
  if (s.new_people.length) {
    const np = s.new_people.slice(0, 2);
    const cont = np.filter(nm => (appear.get(nm) || []).some(yy => yy > s.to));
    cand.push([`${and(np)}に出会ったのもこの時期です。${cont.length ? `${cont[0]}はこの時期のあとも観ています。` : ''}`, np]);
  }
  if (prev) {
    if (s.works * prev.k >= 2 * prev.works * s.k) cand.push(['前の時期より観る本数が増えています。', []]);
    else if (2 * s.works * prev.k <= prev.works * s.k) cand.push(['前の時期より観る本数は減っています。', []]);
  }
  if (nxt) {
    const gone = f.left_venues.filter(([, , b]) => s.from <= b && b <= s.to);
    if (gone.length) cand.push([`${gone[0][0]}には ${gone[0][2]} 年を最後に行っていません。`, [gone[0][0]]]);
  }
  if (s.repeats.length && s.repeats[0][1] >= 3) cand.push([`「${s.repeats[0][0]}」は ${s.repeats[0][1]} 回観ています。`, [s.repeats[0][0]]]);
  let body = '', n = 0;
  const ev = [];
  for (const [text, names] of cand) {
    if (n >= 3 || (body && ulen(body) + ulen(text) > ERA_MAX)) continue;
    body += text;
    n++;
    for (const x of names) if (!ev.includes(x)) ev.push(x);
  }
  return [body || `${s.works} 作品を観ています。`, ev.slice(0, 3)];
}

function yearLine(i, f, appear) {
  const ys = f.years, y = ys[i], p = i ? ys[i - 1] : null;
  let c = [];
  let lead = '';
  if (!p) lead = '記録はこの年から始まります。';
  else if (Number(y.year) - Number(p.year) >= 2) lead = `${p.year} 年以来、${Number(y.year) - Number(p.year)} 年ぶりに観た年です。`;
  const last = ys.at(-1).year;
  const kv = f.kept_venues.find(([, a]) => a === y.year);
  if (kv) {
    const [v, , b, n] = kv;
    c.push([46, b === last ? `${v}に通い始めた年で、いまも通っています。` : `${v}に通い始めた年で、${b} 年まで ${n} 年通いました。`, '']);
  }
  const cont = continued(y, appear);
  if (cont.length) c.push([50, `${cont[0]}と出会い、その後の年も観ています。`, '']);
  else if (y.new_people.length) c.push([32, `${y.new_people[0][0]}と出会った年です。`, '']);
  const tp = p ? topVenue(p) : '', ty = topVenue(y);
  if (tp && ty && tp !== ty) c.push([38, `いちばん通った劇場が${tp}から${ty}に変わりました。`, '']);
  const nv = y.new_venues;
  if (!p && nv.length) c.push([30, `最初に行った劇場は${nv[0]}です。`, '']);
  else if (nv.length >= 2) {
    const k = nv.length;
    c.push([20 + 4 * k, k < 5 ? `${nv[0]}など、初めての劇場が ${k} 館ありました。` : `${nv[0]}など、初めての劇場が 5 館以上ありました。`, '']);
  } else if (nv.length) c.push([14, `${nv[0]}に初めて行きました。`, '']);
  if (p) {
    const a = p.works, b = y.works;
    if (b >= 2 * a && b - a >= 2) c.push([34, `前の年の ${a} 作品から ${b} 作品に増えました。`, '']);
    else if (2 * b <= a && a - b >= 2) c.push([26, `前の年の ${a} 作品から ${b} 作品に減りました。`, '']);
  }
  if (y.repeats.length) {
    const [t, n] = y.repeats[0];
    c.push([n >= 3 ? 24 + 2 * Math.min(n, 10) : 16, `「${t}」を ${n} 回観ています。`, t]);
  }
  const hy = topWord(y.themes), hp = p ? topWord(p.themes) : '';
  if (hy && hp && hp !== hy) c.push([30, `題材が${hp}から${hy}に移りました。`, '']);
  else if (topWord(y.themes, 2)) c.push([22, `題材では${hy}が目立ちます。`, '']);
  else if (topWord(y.tone, 2)) c.push([18, `${topWord(y.tone)}の作品が多い年です。`, '']);
  if (y.loved.length) {
    const k = y.loved.length, t = y.loved[0];
    c.push([10 + 2 * Math.min(k, 6), k === 1 ? `「${t}」にいちばん上の評価を付けています。`
      : k < 6 ? `「${t}」など ${k} 本にいちばん上の評価を付けています。` : `「${t}」など 6 本以上にいちばん上の評価を付けています。`, t]);
  }
  if (ty) c.push([8, `${ty}を中心に観ています。`, '']);
  if (p) c.push([2, '前の年と同じ流れが続いています。', '']);
  c.push([1, `${y.works} 作品を観ています。`, '']);
  c = byDesc(c, x => x[0]);
  if (lead) return ulen(lead) + ulen(c[0][1]) <= YEAR_MAX ? lead + c[0][1] : lead;
  let line = c[0][1];
  for (const [sc, text, title] of c.slice(1, 2)) if (sc >= 8 && ulen(line) + ulen(text) <= YEAR_MAX && !(title && title === c[0][2])) line += text;
  return line;
}

function closingOf(f, eras) {
  const ys = f.years, first = ys[0].year, last = ys.at(-1).year;
  let where = ['', ''];
  const kept = f.kept_venues.filter(([, a, b]) => a === first && b === last).map(x => x[0]);
  const e0 = eras[0], eL = eras.at(-1);
  if (kept.length) where = [`${kept[0]}には記録の初めから通い続けていて、`, `${kept[0]}には記録の初めから通い続けています。`];
  else if (eras.length >= 2 && e0.top && eL.top && e0.top !== eL.top) where = [`通う先は${e0.top}から${eL.top}へ移り、`, `通う先は${e0.top}から${eL.top}へ移ってきました。`];
  else if (eras.length >= 2 && eL.new_venues.length >= 2) where = ['いまも新しい劇場に足を延ばしていて、', 'いまも新しい劇場に足を延ばしています。'];
  const n = ys.length;
  let much = '';
  if (n >= 2) {
    const h = Math.floor(n / 2);
    const a = ys.slice(0, h).reduce((s, y) => s + y.works, 0), b = ys.slice(h).reduce((s, y) => s + y.works, 0);
    much = 2 * b * h >= 3 * a * (n - h) ? '観る本数は年を追って増えています。'
      : 3 * b * h <= 2 * a * (n - h) ? '観る本数は前より落ち着いています。' : '観る本数はほぼ一定です。';
  }
  const out = [];
  if (much) out.push(where[0] + much);
  else if (where[1]) out.push(where[1]);
  if (eras.length >= 2 && e0.theme && eL.theme && e0.theme !== eL.theme) out.push(`題材は${e0.theme}から${eL.theme}へ移っています。`);
  else if (f.long_people.length) {
    const [, nm, a, b, k] = f.long_people[0];
    out.push(`${nm}は ${a} 年から ${b} 年まで ${k} 本観ている、いちばん長く続いている作り手です。`);
  }
  if (!out.length) out.push(`${first} 年から ${last} 年までの ${f.n_works} 作品の記録です。`);
  return out.slice(0, 2).join('');
}

function profileOf(f) {
  const out = [], ev = [];
  const nw = f.n_works, nr = f.n_repeated;
  if (nw >= 3) {
    if (nr >= 2 && 4 * nr >= nw) out.push(`同じ作品に何度も足を運ぶ傾向が記録から見えます（${nw} 作品のうち ${nr} 作品を 2 回以上）。`);
    else if (nr === 0) out.push('同じ作品を 2 度観ることはなく、毎回ちがう作品を選んでいます。');
    else out.push(`多くは 1 回ずつ観ていて、くり返し観たのは ${nr} 作品です。`);
  }
  const t = Object.values(f.verdict_tally).reduce((s, n) => s + n, 0);
  if (t >= 3) {
    if (2 * f.n_loved >= t) out.push(`評価を付けた ${t} 作品のうち ${f.n_loved} 作品がいちばん上で、選んだ作品が当たりやすい傾向が見えます。`);
    else if (4 * f.n_hard >= t) out.push(`低い評価も ${f.n_hard} 作品あり、幅広く試している様子が記録に出ています。`);
  }
  if (f.overall_themes.length && f.overall_themes[0][1] >= 2) {
    const [w, n] = f.overall_themes[0];
    out.push(`題材では${w}の作品を多く観ています（${n} 作品）。`);
    ev.push(w);
  } else if (f.overall_tone.length && f.overall_tone[0][1] >= 2) {
    const [w, n] = f.overall_tone[0];
    out.push(`${w}の作品を多く観ています（${n} 作品）。`);
    ev.push(w);
  }
  if (f.kept_venues.length) {
    const [v, a, b, n] = f.kept_venues[0];
    out.push(`${v}には ${a}〜${b} 年のうち ${n} 年通っていて、決まった劇場に足を運ぶ傾向があります。`);
    ev.push(v);
  }
  return out.length < 2 ? ['', []] : [out.slice(0, 3).join(''), ev.slice(0, 3)];
}

/** chronicle.reading: the eras, a line per year, the profile and the closing, from the facts only. */
export function reading(f) {
  const ys = f.years;
  if (!ys.length) return {eras: [], years: {}, profile: {}, closing: ''};
  const appear = appearOf(f);
  const bounds = [0, ...cutsOf(f, appear), ys.length];
  const sums = bounds.slice(0, -1).map((b, k) => sumEra(ys.slice(b, bounds[k + 1])));
  const eras = sums.map((s, k) => {
    const prev = k ? sums[k - 1] : null, nxt = k + 1 < sums.length ? sums[k + 1] : null;
    const [body, evidence] = eraBody(s, prev, nxt, f, appear);
    return {from: s.from, to: s.to, name: eraName(s, k, nxt === null, prev), body, evidence};
  });
  const [pBody, pEv] = profileOf(f);
  const years = {};
  ys.forEach((y, i) => { years[y.year] = yearLine(i, f, appear); });
  return {eras, years, profile: pBody ? {body: pBody, evidence: pEv} : {}, closing: closingOf(f, sums)};
}

const ym = d => Number(d.slice(0, 4)) * 12 + Number(d.slice(5, 7)) - 1;
const cut = (title, n = 34) => (Array.from(title).length <= n ? title : Array.from(title).slice(0, n).join('') + '…');
/** charts._table */
const table = (head, rows) => `<details class="tv"><summary>数字で見る</summary><table class="tbl mini"><thead><tr>${head.map(h => `<th>${E(h)}</th>`).join('')}</tr></thead>`
  + `<tbody>${rows.map(r => '<tr>' + r.map(c => `<td>${E(c)}</td>`).join('') + '</tr>').join('')}</tbody></table></details>`;

/** chronicle._figure */
function figure(f, read) {
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
  const bands = (read.eras || []).map((e, i) => {
    const a = cx(Number(e.from) * 12), b = cx(Number(e.to) * 12 + 11);
    return `<rect class="eband${i % 2 ? ' alt' : ''}" x="${f1(a)}" y="${f0(TOP - 16)}" width="${f1(Math.max(b - a, 2))}" height="${f0(lanes.length * LH + 16)}" rx="4"/>`
      + `<text class="elab" x="${f1(a + 6)}" y="${f0(TOP - 22)}">${E(e.name)}</text>`;
  });
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
    + `${bands.join('')}${grid.join('')}${rowsSvg.join('')}${dots.join('')}</svg></div>`
    + '<div class="legend chleg"><span class="lg"><svg width="13" height="13" viewBox="0 0 13 13" aria-hidden="true"><circle class="dot on" cx="6.5" cy="6.5" r="4.5"/></svg>' + topOf(marks) + ' を付けた作品</span>'
    + '<span class="lg"><svg width="13" height="13" viewBox="0 0 13 13" aria-hidden="true"><circle class="dot" cx="6.5" cy="6.5" r="4.5"/></svg>そのほかの作品</span>'
    + '<span class="lgn">行は劇場です。<b>初めて行った順</b>に上から並べているので、<b>行の始まりと終わりが通い始めた時期と途切れた時期です。</b>'
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

/** chronicle.panel(works, rated) (the same for the owner and anyone else) */
export function panel(works, rated) {
  const f = facts(works, rated);
  if (!f.years.length) return '';
  const read = reading(f);
  const eraOf = new Map();
  for (const e of read.eras) for (const y of f.years) if (e.from <= y.year && y.year <= e.to && !eraOf.has(y.year)) eraOf.set(y.year, e);
  const shown = new Set();
  const rows = f.years.map(y => {
    const e = eraOf.get(y.year);
    let era = '';
    if (e && !shown.has(e)) {
      shown.add(e);
      era = `<div class="chera"><h3>${E(e.from)}〜${E(e.to)} ${E(e.name)}</h3><p>${E(e.body)}</p>${e.evidence.map(x => `<span class="ev">${E(x)}</span>`).join('')}</div>`;
    }
    const line = read.years[y.year] || '';
    const top = y.venues.length && y.venues[0][1] >= 2 ? y.venues[0][0] : '';
    return era + `<div class="chyear"><div class="chy"><b>${E(y.year)}</b><i>${y.works} 作品・のべ ${y.times} 回</i></div>`
      + `<div class="chbody">${line ? `<p class='chread'>${E(line)}</p>` : ''}${top ? `<p class='chtop'>いちばん通った劇場は${E(top)}です。</p>` : ''}${chips(y, f.links, topOf(f.marks))}</div></div>`;
  }).join('');
  const kept = f.kept_venues.slice(0, 3).map(([v, a, b, n]) => `${v}（${a}〜${b} 年に ${n} 年）`).join('／');
  const longP = f.long_people.slice(0, 3).map(([role, nm, a, b, n]) => `${nm}（${role}・${a}〜${b} 年に ${n} 本）`).join('／');
  const across = kept || longP ? '<div class="chacross"><h3>年をまたいで続いているもの</h3><ul>'
    + (kept ? `<li><b>通い続けている劇場</b>${E(kept)}</li>` : '') + (longP ? `<li><b>何年も観ている作り手</b>${E(longP)}</li>` : '') + '</ul></div>' : '';
  const profile = read.profile.body ? `<div class="chprofile"><h3>この記録から見えること</h3><p>${E(read.profile.body)}</p></div>` : '';
  const closing = read.closing ? `<p class="chclose">${E(read.closing)}</p>` : '';
  const made = '<p class="chnote">この年表の文（時期の名前・年ごとの 1 行・どんな観客であるかの傾向・締めの文）は、'
    + '上に並んでいる事実だけを材料に、決まった規則で書いています。記録が増えると書き変わります。</p>';
  const undated = f.n_undated ? `<p class="chnote">公演日が記録に無い ${f.n_undated} 件は、年に置けないのでこの年表には出していません。「日記帳」には残っています。</p>` : '';
  return `<section class="card chcard wide">
${h2('book', '観劇の年表', `<span class="badge part">${f.n_works} 作品</span>`)}
<p class="lead">記録を年の順に並べ、<b>その年に何が始まったか</b>を出しています。
本数だけでは同じに見える年でも、通う劇場と観る作り手は入れ替わっています。
<b>図の 1 点が 1 作品です。点を押すと、その公演の記録に飛びます。</b></p>
${profile}
${figure(f, read)}
${rows}${across}${closing}
<div class="chfoot">${made}<span class="said"></span></div>
${undated}</section>${CHRONICLE_JS}`;
}
