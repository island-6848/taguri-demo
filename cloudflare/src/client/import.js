// 「公演情報の登録」①: past performances from a Google Calendar or from ticket
// purchase mails. Bundled to public/vendor/import.js by `npm run build:login`
// and loaded by import-loader.js when the card is on screen.
//
// The calendar text and the mails are read here, in the browser. The server
// sees only what was read out: title guesses and dates (to find the stage),
// then the rows the user ticked (to record them).
import PostalMime from 'postal-mime';
import {parseIcs, titleGuesses, readMail, splitPasted, chunkItems} from './import-parse.js';
import {authUrl, CAL_STATE_KEY, CAL_EVENTS_KEY} from './calendar-google.js';

const PACE_MS = 120;              // between requests, well inside the rate limit
const MAIL_MAX = 2 * 1024 * 1024; // a .eml file read at most
const FILES_MAX = 200;            // .eml files read at once
const $ = (root, s) => root.querySelector(s);
const card = () => document.querySelector('[data-import]');
const say = (text, bad = false) => { const s = $(card(), '.said'); if (s) { s.textContent = text; s.classList.toggle('bad', bad); } };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const jstToday = () => new Date(Date.now() + 9 * 3600e3).toISOString().slice(0, 10);
/** At most `n` names, then 「ほか N 件」. */
const names = (list, n = 5) => list.slice(0, n).join('、') + (list.length > n ? ` ほか ${list.length - n} 件` : '');

async function post(path, body) {
  const res = await fetch(path, {method: 'POST', credentials: 'same-origin', headers: {'content-type': 'application/json'}, body: JSON.stringify(body)});
  if (res.status === 429) { await sleep(3000); return post(path, body); }
  const ct = res.headers.get('content-type') || '';
  const data = ct.includes('json') ? await res.json().catch(() => ({})) : null;
  if (!res.ok) throw new Error(data?.error || 'うまくいきませんでした。');
  return data ?? res;
}

// The page's stylesheet is a copy of the demo's (web/), so this card's few rules come with its code.
const css = document.createElement('style');
css.textContent = `.imx-src{margin:10px 0;border-top:1px solid var(--ring);padding-top:8px}
.imx-src summary{cursor:pointer;font-weight:600}
.imx-row{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:8px 0}
.imx-row input[type=url]{flex:1 1 16em;min-width:0}
.imx textarea{width:100%;box-sizing:border-box;font:inherit;font-size:13px}
.imx-list{list-style:none;padding:0;margin:8px 0;max-height:60vh;overflow:auto}
.imx-list li{padding:6px 0;border-bottom:1px solid var(--ring)}
.imx-list label{display:flex;flex-wrap:wrap;gap:4px 8px;align-items:baseline}
.imx-what{flex:1 1 16em;min-width:0;overflow-wrap:anywhere}
.imx-tag,.imx-from,.imx-why{color:var(--ink2)}
.imx-count{font-weight:600}
.imx .said{white-space:pre-line}
.imx .said.bad,.imx-tag.bad{color:var(--warn,#b3261e)}`;
document.head.append(css);

// ------------------------------------------------------------------ state
// found: [{title, date, time, venue, from, stage_id, recorded, matched, checked, tz_unknown, problem}]
let found = [];

const unrecorded = () => found.filter(f => !f.recorded);
/** The count, the bulk buttons and the register button follow the ticks (記録済み is never picked). */
function refresh() {
  const box = card() && $(card(), '.imx-found');
  if (!box) return;
  const n = unrecorded().length, m = found.filter(f => f.checked && !f.recorded).length;
  const count = $(box, '.imx-count'), add = $(box, '[data-imx-add]'), why = $(box, '.imx-why');
  if (count) count.textContent = `未登録候補 ${n} 件／選択 ${m} 件`;
  for (const b of box.querySelectorAll('[data-imx-all]')) b.disabled = !n || m === n;
  for (const b of box.querySelectorAll('[data-imx-none]')) b.disabled = !m;
  if (add) { add.textContent = m ? `選んだ ${m} 件を記録に足す` : '選んだものを記録に足す'; add.disabled = !m; }
  if (why) why.textContent = m ? '' : n ? '足すものに印を付けてください。' : '新しく足せるものはありません（記録済みのものは選べません）。';
}

/** The count and the select-all / clear buttons above the list (the screen's HTML has only the list). */
function tools(box) {
  if ($(box, '.imx-tools')) return;
  const row = document.createElement('div');
  row.className = 'imx-row imx-tools';
  const count = Object.assign(document.createElement('span'), {className: 'imx-count'});
  const all = Object.assign(document.createElement('button'), {type: 'button', textContent: '未登録をすべて選ぶ'});
  all.dataset.imxAll = '1';
  const none = Object.assign(document.createElement('button'), {type: 'button', textContent: '選択をすべて外す'});
  none.dataset.imxNone = '1';
  row.append(count, all, none);
  $(box, '.imx-list').before(row);
  const add = $(box, '[data-imx-add]');
  if (add) add.after(Object.assign(document.createElement('small'), {className: 'imx-why'}));
}

function render(head) {
  const box = $(card(), '.imx-found'), list = $(box, '.imx-list');
  tools(box);
  $(box, '.imx-head').textContent = head;
  list.replaceChildren(...found.map((f, i) => {
    const li = document.createElement('li');
    const label = document.createElement('label');
    const cb = Object.assign(document.createElement('input'), {type: 'checkbox', checked: f.checked && !f.recorded, disabled: f.recorded});
    cb.addEventListener('change', () => { found[i].checked = cb.checked; refresh(); });
    const what = document.createElement('span');
    what.className = 'imx-what';
    // textContent only: nothing read from a mail or a calendar is parsed as HTML
    what.textContent = `${f.date}${f.time ? ' ' + f.time : ''}　${f.title}${f.venue ? '（' + f.venue + '）' : ''}`;
    const tag = document.createElement('small');
    tag.className = 'imx-tag' + (f.problem ? ' bad' : '');
    tag.textContent = (f.recorded ? '記録済み' : f.matched ? '公演と一致' : '公演が見つかりません（このまま足せます）')
      + (f.tz_unknown ? '・時刻はタイムゾーンが分からず、書かれたまま（要確認）' : '') + (f.problem ? `・足せませんでした：${f.problem}` : '');
    const src = document.createElement('small');
    src.className = 'imx-from';
    src.textContent = f.from;
    label.append(cb, what, tag, src);
    li.append(label);
    return li;
  }));
  box.hidden = !found.length;
  refresh();
}

/**
 * items: [{title, guesses, date, time, venue, from}] matched against the catalogue ->
 * {rows, dups, tooBig}: rows to show, items dropped as the same stage and day as another,
 * and items too long to send.
 */
async function match(items, {keepUnmatched}) {
  const out = [];
  const send = p => ({guesses: p.guesses.map(g => g.slice(0, 200)), date: p.date});   // the server reads 200 letters
  const {parts, tooBig} = chunkItems(items, {send});
  let done = 0;
  for (const part of parts) {
    say(`公演と照合しています… ${done + part.length} / ${items.length}`);
    const got = await post('/api/import_match', {items: part.map(send)});
    got.items.forEach((m, n) => {
      const p = part[n];
      if (m.stage_id) out.push({...p, title: m.title, venue: p.venue || m.venue, stage_id: m.stage_id, matched: true, recorded: m.recorded, checked: !m.recorded});
      else if (keepUnmatched) out.push({...p, stage_id: '', matched: false, recorded: false, checked: false});
    });
    done += part.length;
    if (done < items.length) await sleep(PACE_MS);
  }
  // One row per stage and day (a calendar may hold the same visit twice).
  const seen = new Set(), dups = [];
  const rows = out.filter(f => { const k = `${f.stage_id || f.title}@${f.date}`; if (seen.has(k)) { dups.push(f); return false; } seen.add(k); return true; })
    .sort((a, b) => b.date.localeCompare(a.date));
  return {rows, dups, tooBig};
}

// ------------------------------------------------------------------ calendar
const fromCalendar = (text, from) => fromEvents(parseIcs(text), from);
/** capped / since: the Google path left older events out (calendar-google.js googleEvents). */
async function fromEvents(all, from, {capped = false, since = ''} = {}) {
  const today = jstToday();
  const bad = all.filter(e => e.bad);
  // One per title and day (the same visit is often in two calendars).
  const seen = new Set();
  const events = all.filter(e => !e.bad && !e.recurring && e.date && e.date <= today && !seen.has(e.summary + '@' + e.date) && seen.add(e.summary + '@' + e.date));
  const notes = [];
  if (capped) notes.push(`予定が多いため、新しい方から読みました${since ? `（${since} 以降）` : ''}。それより前の公演は、期間を区切って書き出した .ics ファイルから読み込めます。`);
  if (bad.length) notes.push(`日付や時刻が実在しない予定 ${bad.length} 件は除きました：${names(bad.map(e => e.summary))}`);
  if (!events.length) { say(['過去の予定が見つかりませんでした。', ...notes].join('\n'), true); return; }
  const items = events.map(e => ({title: e.summary, guesses: titleGuesses(e.summary), date: e.date, time: e.time, venue: e.location.split(/[,、]/)[0].slice(0, 80), from, tz_unknown: Boolean(e.tz_unknown)}));
  const {rows, tooBig} = await match(items, {keepUnmatched: false});
  found = rows;
  if (tooBig.length) notes.push(`題名が長すぎて照合できなかった予定 ${tooBig.length} 件：${names(tooBig.map(e => e.title.slice(0, 40)))}`);
  const tz = found.filter(f => f.tz_unknown).length;
  if (tz) notes.push(`${tz} 件はタイムゾーンが分からず、時刻を書かれたまま出しています。確かめてから足してください。`);
  const n = found.filter(f => !f.recorded).length;
  say([found.length ? '' : `予定 ${events.length} 件の中に、公演と一致するものはありませんでした。題名の入っていない予定は照合できません。`, ...notes].filter(Boolean).join('\n'), !found.length);
  render(`予定 ${events.length} 件のうち、${found.length} 件が公演と一致しました（新しく足せるのは ${n} 件です）。公演と一致しなかった予定は出していません。`);
}

async function calendarUrl() {
  const url = $(card(), '#imx-url').value.trim();
  if (!url) { say('アドレスを貼ってください。', true); return; }
  say('カレンダーを読み込んでいます…');
  const res = await post('/api/calendar_ics', {url});
  await fromCalendar(await res.text(), 'Google カレンダー');
}

// One button: go to Google, allow reading the calendar, and come back. The page Google
// returns to (/oauth/calendar, calendar-callback.js) reads the events in the browser
// and leaves them in sessionStorage; they are picked up below when this card is shown.
async function googleCalendar() {
  const res = await fetch('/api/auth/config', {credentials: 'omit'});
  const config = res.ok ? await res.json() : {};
  if (!config.calendarClientId) { say('Google カレンダーからの取り込みは、まだ準備中です。下のアドレスかファイルから読み込んでください。', true); return; }
  const state = [...crypto.getRandomValues(new Uint8Array(16))].map(b => b.toString(16).padStart(2, '0')).join('');
  try { sessionStorage.setItem(CAL_STATE_KEY, state); } catch { say('このブラウザでは保存が止められているため、使えません。', true); return; }
  location.assign(authUrl(config.calendarClientId, location.origin, state));
}
function pickUpGoogle() {
  let got = null;
  try { got = JSON.parse(sessionStorage.getItem(CAL_EVENTS_KEY) || 'null'); sessionStorage.removeItem(CAL_EVENTS_KEY); } catch { got = null; }
  // {events, capped, since}; a plain list is what an older callback page left.
  if (Array.isArray(got)) got = {events: got};
  if (!got || !Array.isArray(got.events) || !card()) return;
  card().querySelector('.imx-src')?.setAttribute('open', '');
  run(() => fromEvents(got.events, 'Google カレンダー', {capped: Boolean(got.capped), since: String(got.since || '')}));
}

// ------------------------------------------------------------------ mails
function htmlText(html) {
  const doc = new DOMParser().parseFromString(String(html).replace(/<(br|\/p|\/div|\/tr|\/li|\/h\d)[^>]*>/gi, '$&\n'), 'text/html');
  return doc.body?.textContent || '';
}

/**
 * mails: [{name, from, subject, text}] (name: the file name, or 「N 通目」 for pasted text).
 * files: what happened before reading, for .eml files: {total, over, broken, same, beyond}
 * (lists of names). The breakdown names only files / titles, never a mail's body.
 */
async function fromMails(mails, {unit = '通', files = null} = {}) {
  const items = [], unread = [];
  for (const m of mails) {
    const got = readMail(m);
    if (got.skip) { unread.push(`${m.name}${got.title ? `（${got.title}）` : ''}：${got.skip}`); continue; }
    items.push({title: got.title, guesses: [got.title], date: got.date, time: got.time, venue: got.venue, name: m.name, from: got.site + (got.date_unsure ? '・日付は要確認' : '')});
  }
  const f = files || {total: mails.length, over: [], broken: [], same: [], beyond: 0};
  let rows = [], dups = [], tooBig = [];
  if (items.length) ({rows, dups, tooBig} = await match(items, {keepUnmatched: true}));
  const recorded = rows.filter(r => r.recorded).length, added = rows.length - recorded;
  const parts = [[`候補に追加`, added], ['記録済み', recorded], ['重複', f.same.length + dups.length],
    ['読み取れない', unread.length + f.broken.length], ['大きすぎる', f.over.length + tooBig.length], ['読んでいない', f.beyond]]
    .filter(([, n]) => n).map(([k, n]) => `${k} ${n} ${unit}`);
  const lines = [`${files ? `選んだファイル ${f.total} 件` : `貼ったメール ${f.total} 通`}の内訳：${parts.join('・')}`];
  if (f.over.length) lines.push(`・2MB を超えて読めない：${names(f.over)} → 本文をコピーして上の欄に貼ってください。`);
  if (f.broken.length) lines.push(`・メールとして開けない：${names(f.broken)} → メールソフトで .eml として保存し直すか、本文を貼ってください。`);
  if (unread.length) lines.push(`・公演を読み取れない：${names(unread, 3)} → 公演名・日付が本文にあれば、②の手入力で足せます。`);
  if (f.same.length + dups.length) lines.push(`・同じメール・同じ公演と日付が重なったもの：${names([...f.same, ...dups.map(d => d.name)])}（1 件にまとめました）`);
  if (tooBig.length) lines.push(`・題名が長すぎて照合できない：${names(tooBig.map(t => t.name))} → ②の手入力で足してください。`);
  if (f.beyond) lines.push(`・${FILES_MAX + 1} 件目以降の ${f.beyond} 件は読んでいません。${FILES_MAX} 件ずつ選んでください。`);
  if (!items.length) { say(lines.join('\n'), true); return; }
  found = rows;
  say(lines.join('\n'), lines.length > 1);
  render(`${files ? `ファイル ${f.total} 件` : `メール ${f.total} 通`}から ${items.length} 件を読み取りました。確かめて、足すものに印を付けてください。`);
}

async function emlFiles(all) {
  const files = all.slice(0, FILES_MAX);
  const info = {total: all.length, over: [], broken: [], same: [], beyond: all.length - files.length};
  const mails = [], seen = new Set();
  for (const file of files) {
    if (file.size > MAIL_MAX) { info.over.push(file.name); continue; }
    let email;
    try { email = await PostalMime.parse(await file.arrayBuffer()); } catch { info.broken.push(file.name); continue; }
    const text = email.text || htmlText(email.html || '');
    if (!text.trim()) { info.broken.push(file.name); continue; }
    // The same mail saved twice: the same Message-ID, or the same sender, subject and body.
    const key = email.messageId || `${email.from?.address}\n${email.subject}\n${text}`;
    if (seen.has(key)) { info.same.push(file.name); continue; }
    seen.add(key);
    mails.push({name: file.name, from: email.from?.address || '', subject: email.subject || '', text});
  }
  await fromMails(mails, {unit: '件', files: info});
}

// ------------------------------------------------------------------ record
async function addChecked() {
  const pick = found.filter(f => f.checked && !f.recorded);
  if (!pick.length) { say('足すものに印を付けてください。', true); return; }
  const send = f => ({title: f.title.slice(0, 200), date: f.date, time: f.time, venue: (f.venue || '').slice(0, 80), stage_id: f.stage_id});
  const {parts, tooBig} = chunkItems(pick, {send});
  let added = 0, skipped = 0, done = 0;
  const failed = [];
  for (const f of tooBig) failed.push([f, '長すぎて送れません。②の手入力で足してください']);
  for (const part of parts) {
    say(`記録に足しています… ${done + part.length} / ${pick.length}`);
    let got;
    // A part the server turns down (every item in it wrong) does not stop the others.
    try { got = await post('/api/import_works', {items: part.map(send)}); }
    catch (e) { for (const f of part) failed.push([f, e.message]); done += part.length; continue; }
    added += got.added; skipped += got.skipped;
    const why = new Map((got.rejected || []).map(r => [r.index, r.reason]));
    part.forEach((f, n) => { if (why.has(n)) failed.push([f, why.get(n)]); else { f.recorded = true; f.checked = false; f.problem = ''; } });
    done += part.length;
    if (done < pick.length) await sleep(PACE_MS);
  }
  for (const [f, reason] of failed) f.problem = reason;
  render(`${added} 件を記録に足しました${skipped ? `（${skipped} 件はもう記録してありました）` : ''}。評価は「観た公演の評価」で付けられます。`);
  say(failed.length ? `足せなかったもの ${failed.length} 件：${names(failed.map(([f, r]) => `${f.date} ${f.title.slice(0, 40)}（${r}）`), 3)}` : '', failed.length > 0);
}

function pickAll(on) {
  for (const f of found) f.checked = on && !f.recorded;
  for (const [i, cb] of [...card().querySelectorAll('.imx-list input[type=checkbox]')].entries()) cb.checked = found[i]?.checked || false;
  refresh();
}

// ------------------------------------------------------------------ events
const busy = on => card()?.querySelectorAll('button, input, textarea').forEach(el => { if (!el.closest('.imx-list')) el.disabled = on; });
async function run(fn) {
  busy(true);
  try { await fn(); } catch (e) { say(e.message || 'うまくいきませんでした。', true); }
  busy(false);
  refresh();
}

document.addEventListener('click', ev => {
  const b = ev.target.closest && ev.target.closest('[data-import] button');
  if (!b) return;
  if (b.dataset.imxCal) run(calendarUrl);
  else if (b.dataset.imxGoogle) run(googleCalendar);
  else if (b.dataset.imxMail) run(() => {
    const parts = splitPasted($(card(), '#imx-text').value);
    if (!parts.length) { say('メールの本文を貼ってください。', true); return null; }
    return fromMails(parts.map((text, n) => ({name: `${n + 1} 通目`, text})));
  });
  else if (b.dataset.imxAdd) run(addChecked);
  else if (b.dataset.imxAll) pickAll(true);
  else if (b.dataset.imxNone) pickAll(false);
});
document.addEventListener('change', ev => {
  const input = ev.target;
  if (!input.closest || !input.closest('[data-import]') || input.type !== 'file' || !input.files?.length) return;
  if (input.id === 'imx-ics') run(async () => { await fromCalendar(await input.files[0].text(), 'カレンダーのファイル'); input.value = ''; });
  if (input.id === 'imx-eml') run(async () => { await emlFiles([...input.files]); input.value = ''; });
});

// Coming back from Google (calendar-callback.js) with the events read there.
pickUpGoogle();
