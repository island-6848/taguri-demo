// おすすめのカードの日程（起案者の指示 2026-10-17）:
// - 会場ごとに 1 行「10/28〜11/1　恵比寿・エコー劇場（東京都）」。ツアーのときは、おすすめに出ている会場の
//   日付の前に ★ を付ける（「このおすすめの日程」の札も、行の帯もやめた）
// - 各行の下に、公演日時の暦（日〜土の週ごと。開演の時刻を日に並べ、上演期間の中で公演の無い日は「休演」。
//   読めなかった行の日は「休演」と言い切らず「公式で確認」。#76）。
//   公演ページの「タイムテーブル」の文（「10月23日(金) 歩13:00／印18:00」のような行）から読む
// - 料金が会場によって違うときは、各行に料金の表（券種と金額）を付ける
import {E} from './py.js';

const DAY = 86400000;
// 暦は日曜はじまり（起案者の指示 2026-10-18「ツアー日程の公演日時のカレンダー、日曜始まりにして」）
const WEEK = ['日', '月', '火', '水', '木', '金', '土'];
const MAX_WEEKS = 10;            // これより長い公演は暦にしない（公式サイトを見てもらう）
const iso = ms => new Date(ms).toISOString().slice(0, 10);
const ms = d => Date.parse(d + 'T00:00:00Z');
const md = d => `${Number(d.slice(5, 7))}/${Number(d.slice(8, 10))}`;
// 回の印（Wキャストの「歩」「印」など）にしない字
const NOT_MARK = /[\d\s:：/／、,，.。()（）\[\]［］「」『』【】~〜～\-ー・開演場時分午前後休夜昼※とや回各日]/u;

// 「10月22日(木)〜23日(金) 各19:00」「10/30(金)〜11/1(日)」のような期間の行（起案者の指摘 #76: 読めない期間の日を
// 「休演」と出していた）。1: 前の字、2-5: 初めの日（月・日 か 月/日）、6-9: 終わりの日、10: 残り
const PAREN = String.raw`\s*(?:[(（][^)）]*[)）])?\s*`;
const DT = String.raw`(?:(?:(\d{1,2})月)?(\d{1,2})日|(?<![\d/])(\d{1,2})\/(\d{1,2}))`;
const RANGE_LINE = new RegExp(`^(.*?)${DT}${PAREN}[~〜～]${PAREN}${DT}${PAREN}(.*)$`, 'u');
const MAX_RANGE = 62;            // これより長い期間の行は、日ごとの公演の行とみなさない
// 午前 12 時は 0 時、午後 12 時は 12 時（#77: 「午前12時30分」を 12:30 と読んでいた）
const hour = (ap, h) => (ap === '午後' && h < 12 ? h + 12 : ap === '午前' && h === 12 ? 0 : h);

/** One day's text -> {list: [{t, m}], found, dash}: the performances it names (開場・終演の時刻は落とす). */
function slots(raw) {
  // 「19時」「14時半」「1830開演」も時刻に直す。開場・受付・終演の時刻は公演の回ではないので落とす
  const after = raw
    .replace(/(午前|午後)?\s*(?<!\d)(\d{1,2})時(?!間)(?:(\d{1,2})分|(半))?/g, (_, ap, h, mi, half) => `${hour(ap, +h)}:${half ? '30' : String(mi || 0).padStart(2, '0')}`)
    .replace(/(午前|午後)\s*(\d{1,2}):(\d{2})/g, (_, ap, h, mi) => `${hour(ap, +h)}:${mi}`)
    .replace(/(?<!\d)([012]\d)([0-5]\d)(?=\s*開演)/g, '$1:$2')
    .replace(/(?:開場|受付(?:開始)?|終演)(?:・開場)?\s*[:：]?\s*\d{1,2}:\d{2}|\d{1,2}:\d{2}\s*(?:終演|開場)/g, '');
  const list = [];
  // 印は時刻の前（「歩13:00」）か後ろ（「19:00 A」）の 1 字。0:00〜23:59 の外の時刻（「29:99」）は時刻にしない
  for (const m of after.matchAll(/(?:([^\s\d])\s*)?(?<!\d)(\d{1,2}):(\d{2})(?:\s?([A-Za-z]|[^\x00-\x7F])(?=$|[\s/／、,]))?/gu)) {
    if (Number(m[2]) > 23 || Number(m[3]) > 59) continue;
    const pre = m[1] && !NOT_MARK.test(m[1]) ? m[1] : '';
    const post = m[4] && !NOT_MARK.test(m[4]) && m[4] !== '貸' ? m[4] : '';
    list.push({t: `${Number(m[2])}:${m[3]}`, m: pre || post});
  }
  // 貸切の回（一般には売らない回）も、その日の公演として出す
  for (const _ of after.match(/貸切/g) || []) list.push({t: '貸切', m: ''});
  if (!list.length) for (const w of after.match(/マチネ|ソワレ|昼|夜/g) || []) list.push({t: w, m: ''});
  return {list, found: list.length > 0, dash: /[-ー‐－―]/.test(after.replace(/[(（][^)）]*[)）]/g, ''))};
}

/**
 * The performances read from a timetable text: Map 'YYYY-MM-DD' -> [{t: '13:00' | 'マチネ' | '', m: '歩' | ''}].
 * Lines with one date, and ranges whose days all have the same times (「22日(木)〜23日(金) 各19:00」);
 * the year is the one that puts the date near the run (start..end).
 * The Map also carries `closed` (days the text says have no performance: 「休演」「- -」) and `unknown`
 * (days of lines it could not read: ranges without 「各」, lines with several dates). timetableGrid writes
 * 「休演」 only on days it knows, and 「公式で確認」 on the unknown ones (#76).
 */
export function parseTimetable(text, start, end) {
  const out = new Map();
  out.closed = new Set();
  out.unknown = new Set();
  if (!/^\d{4}-\d{2}-\d{2}$/.test(start || '')) return out;
  const last = /^\d{4}-\d{2}-\d{2}$/.test(end || '') ? end : start;
  const lo = ms(start) - 14 * DAY, hi = ms(last) + 14 * DAY;
  const y0 = Number(start.slice(0, 4));
  const dateOf = (M, D) => {
    for (const y of [y0, y0 + 1, y0 - 1]) {
      const d = `${y}-${String(M).padStart(2, '0')}-${String(D).padStart(2, '0')}`;
      const t = ms(d);
      if (!Number.isNaN(t) && iso(t) === d && t >= lo && t <= hi) return d;
    }
    return '';
  };
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
    // 期間の行: その期間の毎日を 1 つの行として読む（中身は下の 2 つめの繰り返しで）
    const r = RANGE_LINE.exec(line);
    if (r && !/\d\s*(?:月|日|\/)/.test(r[1])) {
      const M1 = Number(r[2] || r[4] || month), D1 = Number(r[3] || r[5]);
      const M2 = Number(r[6] || r[8] || M1), D2 = Number(r[7] || r[9]);
      const a = M1 && dateOf(M1, D1), b = M1 && dateOf(M2, D2);
      if (a && b && a <= b && (ms(b) - ms(a)) / DAY < MAX_RANGE) {
        const span = [];
        for (let t = ms(a); t <= ms(b); t += DAY) span.push(iso(t));
        // 上演期間そのものを書いた見出しの行（時刻が無い）は、日ごとの公演の行ではない
        const whole = a <= start && b >= last && !/\d:\d{2}|\d時(?!間)|休演|各/.test(r[10]);
        open = whole ? null : {dates: span, text: r[10], timed: /\d:\d{2}|\d時(?!間)/.test(r[10]), range: true};
        if (open) days.push(open);
        continue;
      }
    }
    let dates = [...line.matchAll(/(\d{1,2})月(\d{1,2})日|(?:^|[^\d/])(\d{1,2})\/(\d{1,2})(?=\s*[(（])/g)];
    if (!dates.length && month) dates = [...line.matchAll(/^()()()()(\d{1,2})日/g)];
    if (dates.length !== 1) {
      if (!dates.length && open && !open.timed && line.length <= 40 && CONT.test(line)) open.text += ' ' + line;
      else open = null;
      // 日付が 2 つ以上ある行は読まない。その日は「休演」ではなく「公式で確認」にする
      for (const dm of dates) { const d = dateOf(Number(dm[1] || dm[3]), Number(dm[2] || dm[4])); if (d) out.unknown.add(d); }
      continue;
    }
    const dm = dates[0], M = Number(dm[1] || dm[3] || month), D = Number(dm[2] || dm[4] || dm[5]);
    const rest = line.slice(dm.index + dm[0].length);
    // 上の RANGE_LINE で読めなかった期間の行（「10月21日(水)〜25日」で終わりが分からない など）は 1 日の行ではない
    if (/^\s*(?:[(（][^)）]*[)）])?\s*[~〜～]\s*\d/.test(rest)) { open = null; const d = dateOf(M, D); if (d) out.unknown.add(d); continue; }
    const date = dateOf(M, D);
    if (!date) { open = null; continue; }
    // 日付の行に時刻があれば、その下の行（「●13:15開場」のような注意書き）は続きにしない
    open = {dates: [date], text: rest, timed: /\d:\d{2}|\d時(?!間)/.test(rest)};
    days.push(open);
  }
  for (const {dates, text: raw, range} of days) {
    if (/休演/.test(raw)) { for (const d of dates) out.closed.add(d); continue; }
    const {list, found, dash} = slots(raw);
    // 期間の行は「各19:00」のように毎日同じと書いてあるときだけ読む。そうでなければ、その日は「公式で確認」
    if (range && !(found && /各/.test(raw))) { for (const d of dates) out.unknown.add(d); continue; }
    // 時刻の欄が「- -」だけの日は公演が無い（休演）。何も書いていない日は、時刻の分からない公演
    if (!found && dash) { for (const d of dates) out.closed.add(d); continue; }
    for (const d of dates) out.set(d, [...(out.get(d) || []), ...(found ? list : [{t: '', m: ''}])]);
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

// 公演が分からない日（読めなかった行の日で、公演の日でも休演と書かれた日でもない）
const unsure = (perf, d) => !perf.has(d) && !perf.closed?.has(d) && Boolean(perf.unknown?.has(d));
/** Whether the run (from..to) has a day of unsure(): the count of performances is then a lower bound. */
export const unsureIn = (perf, from, to) => [...(perf.unknown || [])].some(d => d >= from && d <= to && unsure(perf, d));

/** The weekly calendar of one venue ('' when there is nothing to draw). `texts`: the stage page's texts for the legend. */
export function timetableGrid(perf, start, end, today, texts = []) {
  if (!perf.size || !start) return '';
  const last = /^\d{4}-\d{2}-\d{2}$/.test(end || '') ? end : start;
  const days = [...perf.keys()].sort();
  const from = days[0] < start ? days[0] : start, to = days.at(-1) > last ? days.at(-1) : last;
  const mon = ms(from) - new Date(ms(from)).getUTCDay() * DAY;   // その週の日曜
  const weeks = Math.ceil((ms(to) - mon + DAY) / (7 * DAY));
  if (weeks > MAX_WEEKS) return '';
  const head = WEEK.map((w, i) => `<th${i === 6 ? ' class="sat"' : i === 0 ? ' class="sun"' : ''}>${w}</th>`).join('');
  const rows = [];
  for (let w = 0; w < weeks; w++) {
    const cells = [];
    for (let i = 0; i < 7; i++) {
      const d = iso(mon + (w * 7 + i) * DAY);
      const inRun = d >= from && d <= to;
      const label = (w === 0 && i === 0) || d.slice(8) === '01' || d === from ? md(d) : String(Number(d.slice(8)));
      const ps = perf.get(d) || [];
      const cls = [i === 6 ? 'sat' : i === 0 ? 'sun' : '', d < today ? 'past' : '', !inRun ? 'out' : ''].filter(Boolean).join(' ');
      // 公演の無い日のうち、タイムテーブルの行を読めなかった日（期間の行など）は「休演」と言い切らない（#76）
      const body = !inRun ? '' : ps.length
        // 印は時刻のすぐ後ろに（起案者の指示 2026-10-18「今図形（改行）時刻、になってるけど時刻のすぐ後ろに図形つけて」）
        ? ps.map(p => `<span class="tm">${E(p.t || '公演')}${p.m ? `<i>${E(p.m)}</i>` : ''}</span>`).join('')
        : unsure(perf, d) ? '<span class="unk">公式で確認</span>' : '<span class="off">休演</span>';
      cells.push(`<td${cls ? ` class="${cls}"` : ''}><span class="d">${E(label)}</span>${body}</td>`);
    }
    rows.push(`<tr>${cells.join('')}</tr>`);
  }
  const n = [...perf.values()].reduce((a, ps) => a + ps.length, 0);
  const more = unsureIn(perf, from, to);
  const marks = [...new Set([...perf.values()].flat().map(p => p.m).filter(Boolean))];
  // 印（★・◆・A/B など）の意味は公演ごとに違うので、その公演のページの説明を書く。説明が無い印はそう書く
  const legend = markLegend(marks, texts);
  const missing = marks.filter(m => !legend.has(m));
  const note = !marks.length ? '' : '<ul class="ttb-legend">'
    + [...legend].map(([m, d]) => `<li><b>${E(m)}</b>${E(d)}</li>`).join('')
    + (missing.length ? `<li class="miss"><b>${missing.map(E).join('・')}</b>公演ページに印の説明がありません</li>` : '') + '</ul>';
  const why = more ? '<p class="ttb-note">「公式で確認」の日は、タイムテーブルの書き方を読み取れなかった日です。公演の有無と時刻は公演ページで確かめてください。</p>' : '';
  return `<table class="ttb" aria-label="公演日時（${n} 回${more ? '以上' : ''}）"><thead><tr>${head}</tr></thead><tbody>${rows.join('')}</tbody></table>${why}${note}`;
}

// 値段の幅だけの行（「2,750円 ~ 7,150円」）
const RANGE = /^[\d,]+円\s*[~〜～\-－]\s*[\d,]+円$/;
/**
 * 両端が同じ額の幅（「12,000円 ~ 12,000円」）を「12,000円」と 1 つだけ書く（起案者の指示 2026-10-18「値段帯が12000円〜12000円って
 * 同一金額になってるときは、簡潔に12000円と明記して」）。web/app.js の sameYen と同じ
 */
export const sameYen = line => line.replace(/([\d,]+)円\s*[~〜～\-－]\s*([\d,]+)円/g, (all, a, b) => (a.replace(/,/g, '') === b.replace(/,/g, '') ? a + '円' : all));
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
  // 幅だけの行かどうかは書き換える前の文で見る（「12,000円 ~ 12,000円」も幅だけの行として明細があれば外す）
  return (dropRange && rest.length ? rest : uniq).map(r => r.map(sameYen));
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
    // いま上演中の会場（初日から千穐楽までに今日が入る）は「・」を「●」に（起案者の指示 2026-10-18）。絞り込んだ県の会場は「★」のまま
    const live = v.start <= today && today <= end;
    const mark = isHere ? '<span class="tf-star" title="絞り込んだ都道府県の会場">★</span>'
      : live ? '<span class="tf-dot live" title="いま上演中">●</span>' : '<span class="tf-dot" aria-hidden="true">・</span>';
    const head = `<span class="tf-when">${tour ? mark : ''}${E(when)}`
      + (grid && n ? `<span class="tf-cnt">（${n} 回${unsureIn(perf, v.start, end) ? '以上' : ''}）</span>` : '') + '</span>'
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
