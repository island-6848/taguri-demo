// 「公演情報の登録」①: past performances from a Google Calendar or from ticket
// purchase mails. Bundled to public/vendor/import.js by `npm run build:login`
// and loaded by import-loader.js when the card is on screen.
//
// The calendar text and the mails are read here, in the browser. The server
// sees only what was read out: title guesses and dates (to find the stage),
// then the rows the user ticked (to record them).
import PostalMime from 'postal-mime';
import {parseIcs, titleGuesses, readMail, splitPasted} from './import-parse.js';

const CHUNK = 20;                 // items per request (the request body is capped at 8 KB)
const PACE_MS = 120;              // between requests, well inside the rate limit
const $ = (root, s) => root.querySelector(s);
const card = () => document.querySelector('[data-import]');
const say = (text, bad = false) => { const s = $(card(), '.said'); if (s) { s.textContent = text; s.classList.toggle('bad', bad); } };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const jstToday = () => new Date(Date.now() + 9 * 3600e3).toISOString().slice(0, 10);

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
.imx-tag,.imx-from{color:var(--ink2)}
.imx .said.bad{color:var(--warn,#b3261e)}`;
document.head.append(css);

// ------------------------------------------------------------------ state
// found: [{title, date, time, venue, from, stage_id, recorded, matched, checked}]
let found = [];

function render(head) {
  const box = $(card(), '.imx-found'), list = $(box, '.imx-list');
  $(box, '.imx-head').textContent = head;
  list.replaceChildren(...found.map((f, i) => {
    const li = document.createElement('li');
    const label = document.createElement('label');
    const cb = Object.assign(document.createElement('input'), {type: 'checkbox', checked: f.checked, disabled: f.recorded});
    cb.addEventListener('change', () => { found[i].checked = cb.checked; });
    const what = document.createElement('span');
    what.className = 'imx-what';
    // textContent only: nothing read from a mail or a calendar is parsed as HTML
    what.textContent = `${f.date}${f.time ? ' ' + f.time : ''}　${f.title}${f.venue ? '（' + f.venue + '）' : ''}`;
    const tag = document.createElement('small');
    tag.className = 'imx-tag';
    tag.textContent = f.recorded ? '記録済み' : f.matched ? '公演と一致' : '公演が見つかりません（このまま足せます）';
    const src = document.createElement('small');
    src.className = 'imx-from';
    src.textContent = f.from;
    label.append(cb, what, tag, src);
    li.append(label);
    return li;
  }));
  box.hidden = !found.length;
}

/** items: [{title, guesses, date, time, venue, from}] -> found, matched against the catalogue. */
async function match(items, {keepUnmatched}) {
  const out = [];
  for (let i = 0; i < items.length; i += CHUNK) {
    say(`公演と照合しています… ${Math.min(i + CHUNK, items.length)} / ${items.length}`);
    const part = items.slice(i, i + CHUNK);
    const got = await post('/api/import_match', {items: part.map(p => ({guesses: p.guesses, date: p.date}))});
    got.items.forEach((m, n) => {
      const p = part[n];
      if (m.stage_id) out.push({...p, title: m.title, venue: p.venue || m.venue, stage_id: m.stage_id, matched: true, recorded: m.recorded, checked: !m.recorded});
      else if (keepUnmatched) out.push({...p, stage_id: '', matched: false, recorded: false, checked: false});
    });
    if (i + CHUNK < items.length) await sleep(PACE_MS);
  }
  // One row per stage and day (a calendar may hold the same visit twice).
  const seen = new Set();
  return out.filter(f => { const k = `${f.stage_id || f.title}@${f.date}`; if (seen.has(k)) return false; seen.add(k); return true; })
    .sort((a, b) => b.date.localeCompare(a.date));
}

// ------------------------------------------------------------------ calendar
async function fromCalendar(text, from) {
  const today = jstToday();
  const events = parseIcs(text).filter(e => !e.recurring && e.date && e.date <= today);
  if (!events.length) { say('過去の予定が見つかりませんでした。', true); return; }
  const items = events.map(e => ({title: e.summary, guesses: titleGuesses(e.summary), date: e.date, time: e.time, venue: e.location.split(/[,、]/)[0].slice(0, 80), from}));
  found = await match(items, {keepUnmatched: false});
  const n = found.filter(f => !f.recorded).length;
  say(found.length ? '' : `予定 ${events.length} 件の中に、公演と一致するものはありませんでした。題名の入っていない予定は照合できません。`, !found.length);
  render(`予定 ${events.length} 件のうち、公演と一致したもの ${found.length} 件（新しく足せるもの ${n} 件）。公演と一致しなかった予定は出していません。`);
}

async function calendarUrl() {
  const url = $(card(), '#imx-url').value.trim();
  if (!url) { say('アドレスを貼ってください。', true); return; }
  say('カレンダーを読み込んでいます…');
  const res = await post('/api/calendar_ics', {url});
  await fromCalendar(await res.text(), 'Google カレンダー');
}

// ------------------------------------------------------------------ mails
function htmlText(html) {
  const doc = new DOMParser().parseFromString(String(html).replace(/<(br|\/p|\/div|\/tr|\/li|\/h\d)[^>]*>/gi, '$&\n'), 'text/html');
  return doc.body?.textContent || '';
}

async function fromMails(mails) {
  const items = [], skipped = [];
  for (const m of mails) {
    const got = readMail(m);
    if (got.skip) { skipped.push(`${got.title || m.subject || '（件名なし）'}：${got.skip}`); continue; }
    items.push({title: got.title, guesses: [got.title], date: got.date, time: got.time, venue: got.venue, from: got.site + (got.date_unsure ? '・日付は要確認' : '')});
  }
  if (!items.length) { say(`公演を読み取れませんでした（${skipped.length} 通）。${skipped.slice(0, 3).join(' / ')}`, true); return; }
  found = await match(items, {keepUnmatched: true});
  say(skipped.length ? `読み取れなかったメール ${skipped.length} 通：${skipped.slice(0, 5).join(' / ')}` : '');
  render(`メール ${mails.length} 通から ${items.length} 件を読み取りました。確かめて、足すものに印を付けてください。`);
}

async function emlFiles(files) {
  const mails = [];
  for (const file of files) {
    if (file.size > 2 * 1024 * 1024) continue;
    const email = await PostalMime.parse(await file.arrayBuffer());
    mails.push({from: email.from?.address || '', subject: email.subject || '', text: email.text || htmlText(email.html || '')});
  }
  await fromMails(mails);
}

// ------------------------------------------------------------------ record
async function addChecked() {
  const pick = found.filter(f => f.checked && !f.recorded);
  if (!pick.length) { say('足すものに印を付けてください。', true); return; }
  let added = 0, skipped = 0;
  for (let i = 0; i < pick.length; i += CHUNK) {
    const got = await post('/api/import_works', {items: pick.slice(i, i + CHUNK).map(f => ({title: f.title, date: f.date, time: f.time, venue: f.venue, stage_id: f.stage_id}))});
    added += got.added; skipped += got.skipped;
  }
  for (const f of pick) { f.recorded = true; f.checked = false; }
  render(`${added} 件を記録に足しました${skipped ? `（${skipped} 件はもう記録してありました）` : ''}。評価は「観た公演の評価」で付けられます。`);
  say('');
}

// ------------------------------------------------------------------ events
const busy = on => card()?.querySelectorAll('button, input, textarea').forEach(el => { if (!el.closest('.imx-list')) el.disabled = on; });
async function run(fn) {
  busy(true);
  try { await fn(); } catch (e) { say(e.message || 'うまくいきませんでした。', true); }
  busy(false);
}

document.addEventListener('click', ev => {
  const b = ev.target.closest && ev.target.closest('[data-import] button');
  if (!b) return;
  if (b.dataset.imxCal) run(calendarUrl);
  else if (b.dataset.imxMail) run(() => {
    const parts = splitPasted($(card(), '#imx-text').value);
    if (!parts.length) { say('メールの本文を貼ってください。', true); return null; }
    return fromMails(parts.map(text => ({text})));
  });
  else if (b.dataset.imxAdd) run(addChecked);
});
document.addEventListener('change', ev => {
  const input = ev.target;
  if (!input.closest || !input.closest('[data-import]') || input.type !== 'file' || !input.files?.length) return;
  if (input.id === 'imx-ics') run(async () => { await fromCalendar(await input.files[0].text(), 'カレンダーのファイル'); input.value = ''; });
  if (input.id === 'imx-eml') run(async () => { await emlFiles([...input.files].slice(0, 200)); input.value = ''; });
});
