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
const NOT_MARK = /[\d\s:：/／、,，.。()（）\[\]［］「」『』【】~〜～\-ー・開演場時分午前後休夜昼※とや回]/u;

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
  // 日付の行と、その下に続く時刻だけの行（「11月03日( 火 )」の次の行に「13:00 -」。起案者の指摘 2026-10-17 の
  // 「三婆」）をまとめて 1 日分の文にする。続きの行は時刻・「-」・貸切・休演などで始まる短い行だけ
  const days = [];
  let open = null;
  const CONT = /^(?:\S?\s*\d{1,2}(?::\d{2}|時)|[-ー‐－―・]|\S{1,3}回|貸切|休演|マチネ|ソワレ|開場|開演)/;
  for (const raw of String(text || '').normalize('NFKC').split(/\n/)) {
    const line = raw.trim();
    if (!line) continue;
    const head = /^(?:\d{4}年)?\s*(\d{1,2})月\s*$/.exec(line);
    if (head) { month = Number(head[1]); open = null; continue; }
    let dates = [...line.matchAll(/(\d{1,2})月(\d{1,2})日|(?:^|[^\d/])(\d{1,2})\/(\d{1,2})(?=\s*[(（])/g)];
    if (!dates.length && month) dates = [...line.matchAll(/^()()()()(\d{1,2})日/g)];
    if (dates.length !== 1) {
      if (!dates.length && open && !open.timed && line.length <= 40 && CONT.test(line)) open.text += ' ' + line;
      else open = null;
      continue;
    }
    const dm = dates[0], M = Number(dm[1] || dm[3] || month), D = Number(dm[2] || dm[4] || dm[5]);
    // 「10月21日(水)〜25日」のような期間の行は 1 日の行ではない
    if (/^\s*(?:[(（][^)）]*[)）])?\s*[~〜～]\s*\d/.test(line.slice(dm.index + dm[0].length))) { open = null; continue; }
    let date = '';
    for (const y of [y0, y0 + 1, y0 - 1]) {
      const d = `${y}-${String(M).padStart(2, '0')}-${String(D).padStart(2, '0')}`;
      const t = ms(d);
      if (!Number.isNaN(t) && iso(t) === d && t >= lo && t <= hi) { date = d; break; }
    }
    if (!date) { open = null; continue; }
    const rest = line.slice(dm.index + dm[0].length);
    // 日付の行に時刻があれば、その下の行（「●13:15開場」のような注意書き）は続きにしない
    open = {date, text: rest, timed: /\d:\d{2}|\d時(?!間)/.test(rest)};
    days.push(open);
  }
  for (const {date, text: raw} of days) {
    if (/休演/.test(raw)) continue;
    // 「19時」「14時半」「1830開演」も時刻に直す。開場・受付・終演の時刻は公演の回ではないので落とす
    const after = raw
      .replace(/(午前|午後)?\s*(?<!\d)(\d{1,2})時(?!間)(?:(\d{1,2})分|(半))?/g, (_, ap, h, mi, half) => `${ap === '午後' && +h < 12 ? +h + 12 : h}:${half ? '30' : String(mi || 0).padStart(2, '0')}`)
      .replace(/午後\s*(\d{1,2}):(\d{2})/g, (_, h, mi) => `${+h < 12 ? +h + 12 : h}:${mi}`)
      .replace(/(?<!\d)([012]\d)([0-5]\d)(?=\s*開演)/g, '$1:$2')
      .replace(/(?:開場|受付(?:開始)?|終演)(?:・開場)?\s*[:：]?\s*\d{1,2}:\d{2}|\d{1,2}:\d{2}\s*(?:終演|開場)/g, '');
    const list = out.get(date) || [];
    let found = false;
    // 印は時刻の前（「歩13:00」）か後ろ（「19:00 A」）の 1 字
    for (const m of after.matchAll(/(?:([^\s\d])\s*)?(?<!\d)(\d{1,2}):(\d{2})(?:\s?([A-Za-z]|[^\x00-\x7F])(?=$|[\s/／、,]))?/gu)) {
      const pre = m[1] && !NOT_MARK.test(m[1]) ? m[1] : '';
      const post = m[4] && !NOT_MARK.test(m[4]) && m[4] !== '貸' ? m[4] : '';
      list.push({t: `${Number(m[2])}:${m[3]}`, m: pre || post});
      found = true;
    }
    // 貸切の回（一般には売らない回）も、その日の公演として出す
    for (const _ of after.match(/貸切/g) || []) { list.push({t: '貸切', m: ''}); found = true; }
    if (!found) for (const w of after.match(/マチネ|ソワレ|昼|夜/g) || []) { list.push({t: w, m: ''}); found = true; }
    // 時刻の欄が「- -」だけの日は公演が無い（休演）。何も書いていない日は、時刻の分からない公演
    if (!found && /[-ー‐－―]/.test(after.replace(/[(（][^)）]*[)）]/g, ''))) continue;
    if (!found) list.push({t: '', m: ''});
    out.set(date, list);
  }
  return out;
}

const reEsc = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const DATE_LINE = /\d{1,2}月\d{1,2}日|(?:^|\D)\d{1,2}\/\d{1,2}(?:\D|$)/;
/**
 * What each mark means, read from the stage page's texts (起案者の指示 2026-10-17「ちゃんと各公演記載して」):
 * 「★・・・鑑賞マナーゆるめの回」「★：…」「★＝…」「A→…」, or a line that begins with the mark.
 * Lines with a date (the timetable itself) are skipped. Map mark -> description (marks without one are left out).
 */
export function markLegend(marks, texts) {
  const out = new Map();
  const lines = texts.join('\n').normalize('NFKC').split(/\n/).map(x => x.trim()).filter(x => x && !DATE_LINE.test(x));
  for (const m of marks) {
    const e = reEsc(m);
    const sep = new RegExp(`(?:^|[\\s※・、(（])${e}\\s*(?:[=＝:：→]|・{2,}|…+|‥+|\\.{2,})\\s*(.+?)(?=\\s+\\S\\s*(?:[=＝:：]|・{2,})|$)`);
    const head = new RegExp(`^※?\\s*${e}\\s*([^\\s=＝:：].+)$`);
    let desc = '';
    for (const line of lines) { const r = sep.exec(line); if (r) { desc = r[1]; break; } }
    if (!desc) for (const line of lines) { const r = head.exec(line); if (r) { desc = r[1]; break; } }
    desc = desc.replace(/\s+/g, ' ').trim();
    if (desc) out.set(m, desc.length > 70 ? desc.slice(0, 68) + '…' : desc);
  }
  return out;
}

/** The weekly calendar of one venue ('' when there is nothing to draw). `texts`: the stage page's texts for the legend. */
export function timetableGrid(perf, start, end, today, texts = []) {
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
        // 印は時刻のすぐ後ろに（起案者の指示 2026-10-18「今図形（改行）時刻、になってるけど時刻のすぐ後ろに図形つけて」）
        ? ps.map(p => `<span class="tm">${E(p.t || '公演')}${p.m ? `<i>${E(p.m)}</i>` : ''}</span>`).join('')
        : '<span class="off">休演</span>';
      cells.push(`<td${cls ? ` class="${cls}"` : ''}><span class="d">${E(label)}</span>${body}</td>`);
    }
    rows.push(`<tr>${cells.join('')}</tr>`);
  }
  const n = [...perf.values()].reduce((a, ps) => a + ps.length, 0);
  const marks = [...new Set([...perf.values()].flat().map(p => p.m).filter(Boolean))];
  // 印（★・◆・A/B など）の意味は公演ごとに違うので、その公演のページの説明を書く。説明が無い印はそう書く
  const legend = markLegend(marks, texts);
  const missing = marks.filter(m => !legend.has(m));
  const note = !marks.length ? '' : '<ul class="ttb-legend">'
    + [...legend].map(([m, d]) => `<li><b>${E(m)}</b>${E(d)}</li>`).join('')
    + (missing.length ? `<li class="miss"><b>${missing.map(E).join('・')}</b>公演ページに印の説明がありません</li>` : '') + '</ul>';
  return `<table class="ttb" aria-label="公演日時（${n} 回）"><thead><tr>${head}</tr></thead><tbody>${rows.join('')}</tbody></table>${note}`;
}

// 値段の幅だけの行（「2,750円 ~ 7,150円」）
const RANGE = /^[\d,]+円\s*[~〜～\-－]\s*[\d,]+円$/;
/**
 * Price rows of a price text: [[券種, 金額] | [文]]. Lines about sale dates are left out.
 * `dropRange`: leave out the range-only line when there are other rows (ツアーの各会場の行。起案者の指示 2026-10-17）.
 */
export function priceRows(text, {dropRange = false} = {}) {
  const out = [];
  for (const raw of String(text || '').normalize('NFKC').split(/\n+/)) {
    const line = raw.replace(/\s+/g, ' ').trim();
    if (!/円|無料/.test(line) || /発売|受付|抽選|開始|販売/.test(line)) continue;
    const m = /^【?([^:：】]{1,24})】?\s*[:：]\s*(.+)$/.exec(line);
    out.push(m ? [m[1].trim(), m[2].trim()] : [line]);
  }
  const uniq = out.filter((r, i) => out.findIndex(x => x.join('\t') === r.join('\t')) === i);
  const rest = uniq.filter(r => !(r.length === 1 && RANGE.test(r[0])));
  return dropRange && rest.length ? rest : uniq;
}
// お金の絵記号（web/app.js の ICON_P.yen と同じ形）。金額の頭に付ける（起案者の指示 2026-10-17）
export const YEN_ICON = '<svg class="ico" viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
  + '<path d="M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM8.6 7.4 12 12l3.4-4.6M12 12v5.2M9.2 12.6h5.6M9.2 15.2h5.6"/></svg>';
export function priceTable(rows) {
  if (!rows.length) return '';
  return `<span class="lp-ico">${YEN_ICON}</span><table class="ptb">${rows.map(r => (r.length > 1 ? `<tr><th>${E(r[0])}</th><td>${E(r[1])}</td></tr>` : `<tr><td colspan="2">${E(r[0])}</td></tr>`)).join('')}</table>`;
}

/**
 * The tour block of a card: one row per venue (`venues`: stageInfo entries), the shown one with a band,
 * each with its calendar and, when the prices differ, its price table.
 */
export function tourBlock(venues, shown, today, prefs = []) {
  const vs = [...venues].filter(v => v && v.start).sort((a, b) => (a.start < b.start ? -1 : a.start > b.start ? 1 : 0));
  if (!vs.length) return {html: '', perVenuePrice: false};
  const priceOf = v => priceRows(v.fields?.['料金（1枚あたり）'] || v.price || '', {dropRange: true});
  const keys = new Set(vs.map(v => JSON.stringify(priceOf(v))));
  const perVenuePrice = vs.length > 1 && keys.size > 1;
  const rows = vs.map(v => {
    const end = v.end || v.start;
    const when = v.start === end ? md(v.start) : `${md(v.start)}〜${md(end)}`;
    const where = (v.venue || '会場未定') + (v.pref ? `（${v.pref}）` : '');
    const perf = parseTimetable(v.fields?.['タイムテーブル'] || '', v.start, end);
    const f = v.fields || {};
    const grid = timetableGrid(perf, v.start, end, today, [f['タイムテーブル'], f['その他注意事項'], f['公演情報'], f['その他'], f['出演']].filter(Boolean).map(String));
    // ツアー（会場が 2 つ以上）は箇条書き（行頭の「・」）にし、都道府県で絞っているときは、その県の会場の行頭を
    // 「★」にする（起案者の指示 2026-10-18「日程はツアーの場合箇条書きで表現。絞り込んでいる場合は、該当の公演を・→★にして」）
    const tour = vs.length > 1;
    const isHere = tour && prefs.length > 0 && prefs.includes(v.pref);
    const shownRow = vs.length === 1 || (prefs.length ? isHere : String(v.stage_id) === String(shown));   // 暦を開いておく行
    const n = [...perf.values()].reduce((a, ps) => a + ps.length, 0);
    const price = perVenuePrice ? (priceTable(priceOf(v)) || `<p class="lp-none"><span class="lp-ico">${YEN_ICON}</span>料金 不明</p>`) : '';
    // 会場の名前はツアーのときだけ（1 か所なら上の劇場の行と同じなので出さない。起案者の指示 2026-10-17）
    // 公演の回数は、開く前の日程の横に「（N 回）」（起案者の指示 2026-10-18。開いた中の「公演日時（N 回）」の見出しはやめた）
    const head = `<span class="tf-when">${tour ? (isHere ? '<span class="tf-star" title="絞り込んだ都道府県の会場">★</span>' : '<span class="tf-dot" aria-hidden="true">・</span>') : ''}${E(when)}`
      + (grid && n ? `<span class="tf-cnt">（${n} 回）</span>` : '') + '</span>'
      + (tour ? `<span class="tf-loc">${E(where)}</span>` : '');
    const body = (price ? `<div class="tf-price">${price}</div>` : '') + (grid || '');
    const cls = `tf-row${isHere ? ' here' : ''}${end < today ? ' done' : ''}`;
    // 日程の行そのものを押す口にし、行の右に「▶詳細」。開いた中身（料金・暦）は一段右にずらす（起案者の指示 2026-10-17）
    return body
      ? `<details class="${cls}"${shownRow ? ' open' : ''}><summary class="tf-head">${head}<span class="tf-more">詳細</span></summary><div class="tf-body">${body}</div></details>`
      : `<div class="${cls}"><div class="tf-head">${head}</div></div>`;
  });
  // 会場が 1 つなら one: 見出し「日程」の横から書き始める（起案者の指示 2026-10-17）
  return {html: `<div class="tourfull v2${vs.length === 1 ? ' one' : ''}">${rows.join('')}</div>`, perVenuePrice};
}
