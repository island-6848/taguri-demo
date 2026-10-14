// Reading past performances out of a Google Calendar (iCal) and out of ticket
// purchase confirmation mails, in the browser. Nothing here talks to a server:
// the calendar text and the mail bodies stay on the device, and only what is
// read out (title, date, time, venue) is sent to be matched with the catalogue.
//
// The mail rules are a port of tools/tickets/extract_performances.py (the
// owner's Gmail import), one per ticket site: ぴあ, おけぴ, ローチケ, 東宝ナビザーブ,
// the theatre companies' ticket service, and a generic fallback.

// ---------------------------------------------------------------- calendar (RFC 5545)

const pad = n => String(n).padStart(2, '0');
const unescapeText = s => s.replace(/\\([\\;,nN])/g, (_, c) => (c === 'n' || c === 'N' ? '\n' : c));

/** "20251108T190000Z" / "20251108T190000" / "20251108" -> {date, time} in Japan time. */
export function icsDate(value) {
  const m = /^(\d{4})(\d{2})(\d{2})(?:T(\d{2})(\d{2})(\d{2})?(Z)?)?$/.exec(value.trim());
  if (!m) return null;
  const [, y, mo, d, h, mi, , z] = m;
  if (h === undefined) return {date: `${y}-${mo}-${d}`, time: ''};
  if (z) {
    // UTC: Japan is UTC+9 all year (no daylight saving).
    const t = new Date(Date.UTC(+y, +mo - 1, +d, +h, +mi) + 9 * 3600e3);
    return {date: `${t.getUTCFullYear()}-${pad(t.getUTCMonth() + 1)}-${pad(t.getUTCDate())}`, time: `${pad(t.getUTCHours())}:${pad(t.getUTCMinutes())}`};
  }
  // Floating or TZID time: read as written (a theatre visit is put in local time).
  return {date: `${y}-${mo}-${d}`, time: `${h}:${mi}`};
}

/** VEVENTs of an iCal text: [{summary, date, time, location, recurring}]. A theatre visit is
 * never a repeating event, so repeating ones are marked for the caller to leave out. */
export function parseIcs(text) {
  const lines = String(text).replace(/\r\n?/g, '\n').replace(/\n[ \t]/g, '').split('\n');
  const out = [];
  let ev = null;
  for (const line of lines) {
    if (line === 'BEGIN:VEVENT') { ev = {}; continue; }
    if (line === 'END:VEVENT') {
      if (ev && ev.summary && ev.start) out.push({summary: ev.summary, date: ev.start.date, time: ev.start.time, location: ev.location || '', recurring: Boolean(ev.rrule)});
      ev = null;
      continue;
    }
    if (!ev) continue;
    const colon = line.indexOf(':');
    if (colon < 0) continue;
    const head = line.slice(0, colon), value = line.slice(colon + 1);
    const semi = head.indexOf(';');
    const name = (semi < 0 ? head : head.slice(0, semi)).toUpperCase();
    if (name === 'SUMMARY') ev.summary = unescapeText(value).trim();
    else if (name === 'LOCATION') ev.location = unescapeText(value).replace(/\s+/g, ' ').trim();
    else if (name === 'DTSTART') ev.start = icsDate(value);
    else if (name === 'RRULE' || name === 'RECURRENCE-ID') ev.rrule = true;
  }
  return out;
}

// Words people put around a play's title in their own calendar.
const EVENT_NOISE = /^(?:観劇|舞台|演劇|芝居|ミュージカル|ストレートプレイ|公演|チケット|マチネ|ソワレ)\s*[:：・\-－ー]?\s*/;
/**
 * Titles to try for a calendar event, best first: the part in 『』/「」, the
 * summary without 観劇・舞台… and without "@ 劇場" / "（劇場）" / 【…】, and the
 * summary itself. The server keeps only the ones that name a real stage.
 */
export function titleGuesses(summary) {
  const s = String(summary || '').trim();
  const out = [];
  const add = t => { t = t.replace(/\s+/g, ' ').trim(); if (Array.from(t).length >= 2 && !out.includes(t)) out.push(t); };
  for (const m of s.matchAll(/[『「]([^』」]{2,60})[』」]/g)) add(m[1]);
  let t = s.replace(/【[^】]*】|\[[^\]]*\]/g, ' ');
  t = t.replace(/\s*[@＠].*$/, '').replace(/\s*[（(][^）)]*[）)]\s*$/, '');
  for (let i = 0; i < 2; i++) t = t.trim().replace(EVENT_NOISE, '');
  add(t);
  add(s);
  return out.slice(0, 4);
}

// ---------------------------------------------------------------- mails

const DATE = '(20\\d\\d)[/年](\\d{1,2})[/月](\\d{1,2})';
const TIME = '(\\d{1,2})[:：時](\\d{2})';
const ymd = m => `${m[1]}-${pad(+m[2])}-${pad(+m[3])}`;
const hm = (h, mi) => `${pad(+h)}:${mi}`;
const clean = s => s.replace(/\s+/g, ' ').replace(/^[ 　:：]+|[ 　:：]+$/g, '');

// Words for the day of the performance, and words for other days (booking,
// payment, pick-up). From the measured rule in extract_performances.perf_date.
const NEAR = ['開演', '開場', '公演日', '上演', '観劇日', 'ご来場', '来場日'];
const AWAY = ['申込', '購入', '入金', '決済', '発売', '受付', '予約日', '注文', '支払', '期限', '締切', '引取', '引き取り', '発券', '引換', '配信'];
/** The performance day in a mail body, or '' when it cannot be told from the other dates. */
export function perfDate(t) {
  let best = null;
  for (const m of t.matchAll(new RegExp(DATE, 'g'))) {
    const end = m.index + m[0].length;
    const tail = t.slice(end, end + 25);
    const around = t.slice(Math.max(0, m.index - 60), end + 60).replace(/\n/g, ' ');
    const score = /開演|開場/.test(tail) ? 10
      : NEAR.filter(k => around.includes(k)).length * 2 - AWAY.filter(k => around.includes(k)).length * 3;
    if (score > 0 && (!best || score > best[0])) best = [score, ymd(m)];
  }
  return best ? best[1] : '';
}

/** Take off 『』/「」 only when they wrap the whole title (extract_performances.unwrap). */
export function unwrap(s) {
  let t = s.trim(), again = true;
  while (again) {
    again = false;
    for (const [a, b] of [['『', '』'], ['「', '」']]) {
      if (t.length < 2 || !(t.startsWith(a) && t.endsWith(b))) continue;
      let depth = 0, early = false;
      const cs = Array.from(t);
      for (let i = 0; i < cs.length; i++) {
        depth += (cs[i] === a) - (cs[i] === b);
        if (depth === 0 && i < cs.length - 1) { early = true; break; }
      }
      if (!early && depth === 0) { t = cs.slice(1, -1).join('').trim(); again = true; }
    }
  }
  return t;
}

const re = (pattern, t) => new RegExp(pattern).exec(t);

function pia(t) {
  const d = {}; let m;
  if ((m = re('公演名[:：](.+)', t))) d.title = clean(m[1]);
  if ((m = re('公演日[:：]\\s*' + DATE, t))) d.date = ymd(m);
  if ((m = re('開演時刻[:：]\\s*' + TIME, t))) d.time = hm(m[1], m[2]);
  if ((m = re('会場名[:：](.+)', t))) d.venue = clean(m[1].replace(/\(.+?\)/g, ''));
  return d;
}
function okepi(t) {
  const d = {}; let m;
  if ((m = re('\\[公演名\\]\\s*(.+)', t))) d.title = unwrap(clean(m[1]));
  if ((m = re('\\[公演日時\\]\\s*' + DATE, t))) d.date = ymd(m);
  if ((m = re('\\[公演日時\\].*?' + TIME, t))) d.time = hm(m[1], m[2]);
  if ((m = re('\\[劇場\\]\\s*(.+)', t))) d.venue = clean(m[1]);
  return d;
}
function ltike(t) {
  const d = {}; let m;
  if ((m = re('■公演タイトル[　\\s]*[:：](.+)', t))) d.title = clean(m[1]);
  if ((m = re('■公演日[　\\s]*[:：]\\s*' + DATE, t))) d.date = ymd(m);
  if ((m = re('(\\d{1,2})[:：](\\d{2})\\s*開[　\\s]*演', t))) d.time = hm(m[1], m[2]);
  if ((m = re('■会場名[　\\s]*[:：](.+)', t))) d.venue = clean(m[1]);
  return d;
}
function toho(t) {
  const d = {}; let m;
  if ((m = re('■公演名\\s*\\n\\s*(.+)', t))) d.title = clean(m[1]);
  if ((m = re('■劇場\\s*\\n\\s*(.+)', t))) d.venue = clean(m[1]);
  if ((m = re('■公演日時\\s*\\n\\s*' + DATE, t))) d.date = ymd(m);
  if ((m = re('■公演日時[\\s\\S]{0,60}?(\\d{1,2}):(\\d{2})\\s*開演', t))) d.time = hm(m[1], m[2]);
  return d;
}
function gekidan(t) {
  const d = {}; let m;
  if ((m = re('(?:予約|申込)番号[:：]\\s*\\S+\\s*\\n+\\s*(.+)', t))) d.title = unwrap(clean(m[1]).split('★')[0]);
  const head = Math.max(t.indexOf('予約番号'), t.indexOf('申込番号'));
  const part = head >= 0 ? t.slice(head) : t;
  const got = perfDate(part);
  if (got) d.date = got;
  else if ((m = re(DATE + '\\(.\\)', part))) { d.date = ymd(m); d.date_unsure = true; }
  if ((m = re('(\\d{1,2}):(\\d{2})\\s*開演', t))) d.time = hm(m[1], m[2]);
  return d;
}

// What the generic rule would otherwise take for a title (extract_performances).
const NOT_A_TITLE = new Set(['購入履歴', '引換票番号(13桁)', '払込・引換票番号（13桁）', '申込確認', 'マイページ', '会員登録', '購入内容',
  'お申込内容', 'ご購入内容', '予約履歴', '重要', '注意', 'Myチケット', 'マイチケット', '申込状況確認ページ', 'チケットのご利用方法について',
  '決済完了の', 'タイトル未定', '予約／購入履歴', '指定席券売機', '受取コード', '確認コード']);
const NOT_A_TITLE_PARTS = ['マルチコピー機', '券売機', '専用機', '発券', '引換', '払込', '支払', '決済', '手数料', 'セブン', 'ローソン',
  'ファミリーマート', 'コンビニ', '会員登録', 'マイページ', '購入履歴', 'ログイン', '手続き', 'お問合せ', 'お問い合わせ', '利用規約'];
function generic(t) {
  const d = {};
  outer: for (const pat of ['公演名[:：]?\\s*(.+)', '公演タイトル[:：]?\\s*(.+)', '『(.{2,60}?)』', '「(.{2,60}?)」']) {
    for (const m of t.matchAll(new RegExp(pat, 'g'))) {
      const cand = unwrap(clean(m[1]));
      if (cand && !NOT_A_TITLE.has(cand) && !NOT_A_TITLE_PARTS.some(w => cand.includes(w)) && !/^[\d\-（）() 桁]+$/.test(cand)) {
        d.title = cand;
        break outer;
      }
    }
  }
  const got = perfDate(t);
  let m;
  if (got) d.date = got;
  else if ((m = re(DATE, t))) { d.date = ymd(m); d.date_unsure = true; }
  if ((m = re('(\\d{1,2}):(\\d{2})\\s*開演', t))) d.time = hm(m[1], m[2]);
  return d;
}

// Each site: who sends it, and what its body looks like (a pasted mail has no
// sender, so the body's own labels pick the rule).
export const SITES = [
  {name: 'ぴあ', domain: 'pia.co.jp', looks: /公演名[:：]/.source + '[\\s\\S]*' + /会場名[:：]/.source, read: pia},
  {name: 'おけぴ', domain: 'okepi.jp', looks: /\[公演名\]/.source, read: okepi},
  {name: 'ローチケ', domain: 'l-tike.com', looks: /■公演タイトル/.source, read: ltike},
  {name: '東宝ナビザーブ', domain: 'toho-navi.com', looks: /■公演名\s*\n/.source, read: toho},
];

const PICKUP = ['店頭発券', '発券のお知らせ', 'チケット受取', '受取完了', '引換票'];
const NOT_THEATRE = ['CONCERT', 'コンサート', 'LIVE TOUR', 'ライブツアー', 'ドキュメンタリー', 'フェスティバル', 'ミュージアム', '武道館',
  'ZEPP', 'Zepp', '舞台挨拶', '上映', '試写'];
const THEATRE_ANYWAY = ['座長公演', '明治座', '新歌舞伎座', '御園座'];
export const isTheatre = title => THEATRE_ANYWAY.some(w => title.includes(w)) || !NOT_THEATRE.some(w => title.includes(w));

/**
 * One mail -> {title, date, time, venue, site} or {skip: reason}.
 * `from` and `subject` may be empty (a pasted body).
 */
export function readMail({from = '', subject = '', text = ''}) {
  const body = String(text).replace(/\r\n?/g, '\n');
  // A pasted mail may carry its own header lines.
  from ||= /^(?:From|差出人)[:：](.*)$/m.exec(body)?.[1] || '';
  subject ||= /^(?:Subject|件名)[:：](.*)$/m.exec(body)?.[1]?.trim() || '';
  const domain = (/@([^>\s]+)/.exec(from)?.[1] || '').toLowerCase();
  if (PICKUP.some(k => subject.includes(k)) && !/購入確認|購入完了|お申込完了|予約完了|注文確認/.test(subject))
    return {skip: '受け取り・発券の案内で、公演名が書かれていません'};
  let got = null, site = '';
  if (/チケットサービス/.test(body) && /(予約|申込)番号/.test(body)) {
    const g = gekidan(body);
    if (g.title) { got = g; site = '劇団のチケットサービス'; }
  }
  for (const s of SITES) {
    if (got) break;
    if (!(domain && domain.endsWith(s.domain)) && !new RegExp(s.looks).test(body)) continue;
    const g = s.read(body);
    if (g.title) { got = g; site = s.name; }
  }
  if (!got) { got = generic(body); site = 'そのほか'; }
  if (!got.title) return {skip: '公演名を読み取れませんでした'};
  if (!isTheatre(got.title)) return {skip: '演劇ではなさそうです'};
  if (!got.date) return {skip: '公演日を読み取れませんでした', title: got.title};
  return {title: got.title, date: got.date, time: got.time || '', venue: got.venue || '', site, date_unsure: Boolean(got.date_unsure)};
}

/** Pasted text with several mails: split where a new "差出人/From:" header or a long rule starts. */
export function splitPasted(text) {
  const parts = String(text).replace(/\r\n?/g, '\n').split(/\n(?=(?:From|差出人)[:：])|\n[-=─━]{20,}\n/);
  return parts.map(p => p.trim()).filter(p => p.length > 20);
}
