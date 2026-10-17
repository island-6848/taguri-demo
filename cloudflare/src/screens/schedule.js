// おすすめのカードの日程（起案者の指示 2026-10-17）:
// - 会場ごとに 1 行「10/28〜11/1　恵比寿・エコー劇場（東京都）」。ツアーのときは、おすすめに出ている会場の
//   日付の前に ★ を付ける（「このおすすめの日程」の札も、行の帯もやめた）
// - 各行の下に、公演日時の暦（月〜日の週ごと。開演の時刻を日に並べ、上演期間の中で公演の無い日は「休演」）。
//   公演ページの「タイムテーブル」の文（「10月23日(金) 歩13:00／印18:00」のような行）から読む
// - 料金が会場によって違うときは、各行に料金の表（券種と金額）を付ける
import {E} from './py.js';

const DAY = 86400000;
const WEEK = ['月', '火', '水', '木', '金', '土', '日'];
const MAX_WEEKS = 10;            // これより長い公演は暦にしない（公式サイトを見てもらう）
const iso = ms => new Date(ms).toISOString().slice(0, 10);
const ms = d => Date.parse(d + 'T00:00:00Z');
const md = d => `${Number(d.slice(5, 7))}/${Number(d.slice(8, 10))}`;
// 回の印（Wキャストの「歩」「印」など）にしない字
const NOT_MARK = /[\d\s:：/／、,，.。()（）\[\]［］「」『』【】~〜～\-ー・開演場時分午前後休夜昼※とや]/u;

/**
 * The performances read from a timetable text: Map 'YYYY-MM-DD' -> [{t: '13:00' | 'マチネ' | '', m: '歩' | ''}].
 * Only lines with exactly one date; the year is the one that puts the date near the run (start..end).
 */
export function parseTimetable(text, start, end) {
  const out = new Map();
  if (!/^\d{4}-\d{2}-\d{2}$/.test(start || '')) return out;
  const lo = ms(start) - 14 * DAY, hi = ms(/^\d{4}-\d{2}-\d{2}$/.test(end || '') ? end : start) + 14 * DAY;
  const y0 = Number(start.slice(0, 4));
  let month = 0;          // 「10月」「2026年11月」だけの見出しの行の月（その下の「27日（火）…」に使う）
  for (const raw of String(text || '').normalize('NFKC').split(/\n/)) {
    const line = raw.trim();
    const head = /^(?:\d{4}年)?\s*(\d{1,2})月\s*$/.exec(line);
    if (head) { month = Number(head[1]); continue; }
    let dates = [...line.matchAll(/(\d{1,2})月(\d{1,2})日|(?:^|[^\d/])(\d{1,2})\/(\d{1,2})(?=\s*[(（])/g)];
    if (!dates.length && month) dates = [...line.matchAll(/^()()()()(\d{1,2})日/g)];
    if (dates.length !== 1) continue;
    const dm = dates[0], M = Number(dm[1] || dm[3] || month), D = Number(dm[2] || dm[4] || dm[5]);
    // 「10月21日(水)〜25日」のような期間の行は 1 日の行ではない
    if (/^\s*(?:[(（][^)）]*[)）])?\s*[~〜～]\s*\d/.test(line.slice(dm.index + dm[0].length))) continue;
    let date = '';
    for (const y of [y0, y0 + 1, y0 - 1]) {
      const d = `${y}-${String(M).padStart(2, '0')}-${String(D).padStart(2, '0')}`;
      const t = ms(d);
      if (!Number.isNaN(t) && iso(t) === d && t >= lo && t <= hi) { date = d; break; }
    }
    if (!date) continue;
    const after = line.slice(dm.index + dm[0].length);
    if (/休演/.test(after)) continue;
    const list = out.get(date) || [];
    let found = false;
    // 印は時刻の前（「歩13:00」）か後ろ（「19:00 A」）の 1 字
    for (const m of after.matchAll(/(?:(\S)\s*)?(\d{1,2}):(\d{2})(?:\s?([A-Za-z]|[^\x00-\x7F])(?=$|[\s/／、,]))?/gu)) {
      const pre = m[1] && !NOT_MARK.test(m[1]) ? m[1] : '';
      const post = m[4] && !NOT_MARK.test(m[4]) ? m[4] : '';
      const mark = pre || post;
      list.push({t: `${Number(m[2])}:${m[3]}`, m: mark});
      found = true;
    }
    if (!found) for (const w of after.match(/マチネ|ソワレ|昼|夜/g) || []) { list.push({t: w, m: ''}); found = true; }
    if (!found) list.push({t: '', m: ''});
    out.set(date, list);
  }
  return out;
}

/** The weekly calendar of one venue ('' when there is nothing to draw). */
export function timetableGrid(perf, start, end, today) {
  if (!perf.size || !start) return '';
  const last = /^\d{4}-\d{2}-\d{2}$/.test(end || '') ? end : start;
  const days = [...perf.keys()].sort();
  const from = days[0] < start ? days[0] : start, to = days.at(-1) > last ? days.at(-1) : last;
  const mon = ms(from) - ((new Date(ms(from)).getUTCDay() + 6) % 7) * DAY;
  const weeks = Math.ceil((ms(to) - mon + DAY) / (7 * DAY));
  if (weeks > MAX_WEEKS) return '';
  const head = WEEK.map((w, i) => `<th${i === 5 ? ' class="sat"' : i === 6 ? ' class="sun"' : ''}>${w}</th>`).join('');
  const rows = [];
  for (let w = 0; w < weeks; w++) {
    const cells = [];
    for (let i = 0; i < 7; i++) {
      const d = iso(mon + (w * 7 + i) * DAY);
      const inRun = d >= from && d <= to;
      const label = (w === 0 && i === 0) || d.slice(8) === '01' || d === from ? md(d) : String(Number(d.slice(8)));
      const ps = perf.get(d) || [];
      const cls = [i === 5 ? 'sat' : i === 6 ? 'sun' : '', d < today ? 'past' : '', !inRun ? 'out' : ''].filter(Boolean).join(' ');
      const body = !inRun ? '' : ps.length
        ? ps.map(p => `<span class="tm">${p.m ? `<i>${E(p.m)}</i>` : ''}${E(p.t || '公演')}</span>`).join('')
        : '<span class="off">休演</span>';
      cells.push(`<td${cls ? ` class="${cls}"` : ''}><span class="d">${E(label)}</span>${body}</td>`);
    }
    rows.push(`<tr>${cells.join('')}</tr>`);
  }
  const n = [...perf.values()].reduce((a, ps) => a + ps.length, 0);
  const marks = [...new Set([...perf.values()].flat().map(p => p.m).filter(Boolean))];
  // 印（★・◆・A/B など）は、出演者の組やアフタートークなど公演ごとに意味が違うので、公演ページの書き方のまま出す
  const note = marks.length ? `<p class="ttb-note">${marks.map(E).join('・')} の意味は公演ページをご覧ください（出演者の組・アフタートークなど）。</p>` : '';
  return `<table class="ttb" aria-label="公演日時（${n} 回）"><thead><tr>${head}</tr></thead><tbody>${rows.join('')}</tbody></table>${note}`;
}

/** Price rows of a price text: [[券種, 金額] | [文]]. Lines about sale dates are left out. */
export function priceRows(text) {
  const out = [];
  for (const raw of String(text || '').normalize('NFKC').split(/\n+/)) {
    const line = raw.replace(/\s+/g, ' ').trim();
    if (!/円|無料/.test(line) || /発売|受付|抽選|開始|販売/.test(line)) continue;
    const m = /^【?([^:：】]{1,24})】?\s*[:：]\s*(.+)$/.exec(line);
    out.push(m ? [m[1].trim(), m[2].trim()] : [line]);
  }
  return out.filter((r, i) => out.findIndex(x => x.join('\t') === r.join('\t')) === i);
}
export function priceTable(rows) {
  if (!rows.length) return '';
  return `<table class="ptb">${rows.map(r => (r.length > 1 ? `<tr><th>${E(r[0])}</th><td>${E(r[1])}</td></tr>` : `<tr><td colspan="2">${E(r[0])}</td></tr>`)).join('')}</table>`;
}

/**
 * The tour block of a card: one row per venue (`venues`: stageInfo entries), the shown one with a band,
 * each with its calendar and, when the prices differ, its price table.
 */
export function tourBlock(venues, shown, today) {
  const vs = [...venues].filter(v => v && v.start).sort((a, b) => (a.start < b.start ? -1 : a.start > b.start ? 1 : 0));
  if (!vs.length) return {html: '', perVenuePrice: false};
  const priceOf = v => priceRows(v.fields?.['料金（1枚あたり）'] || v.price || '');
  const keys = new Set(vs.map(v => JSON.stringify(priceOf(v))));
  const perVenuePrice = vs.length > 1 && keys.size > 1;
  const rows = vs.map(v => {
    const end = v.end || v.start;
    const when = v.start === end ? md(v.start) : `${md(v.start)}〜${md(end)}`;
    const where = (v.venue || '会場未定') + (v.pref ? `（${v.pref}）` : '');
    const perf = parseTimetable(v.fields?.['タイムテーブル'] || '', v.start, end);
    const grid = timetableGrid(perf, v.start, end, today);
    // おすすめに出ている会場の印は、ツアー（会場が 2 つ以上）のときだけ。帯ではなく日付の前の ★（起案者の指示 2026-10-17）
    const isHere = vs.length > 1 && String(v.stage_id) === String(shown);
    const n = [...perf.values()].reduce((a, ps) => a + ps.length, 0);
    const price = perVenuePrice ? priceTable(priceOf(v)) : '';
    return `<div class="tf-row${isHere ? ' here' : ''}${end < today ? ' done' : ''}"><div class="tf-head"><span class="tf-when">${isHere ? '<span class="tf-star" title="おすすめに出ている会場">★</span>' : ''}${E(when)}</span>`
      + `<span class="tf-loc">${E(where)}</span></div>`
      + (price ? `<div class="tf-price">${price}</div>` : '')
      + (grid ? `<details class="tf-tt"${isHere ? ' open' : ''}><summary>公演日時（${n} 回）</summary>${grid}</details>` : '')
      + '</div>';
  });
  return {html: `<div class="tourfull v2">${rows.join('')}</div>`, perVenuePrice};
}
