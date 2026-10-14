// 「公演情報の登録」①: reading a Google Calendar and purchase mails in the
// browser (src/client/import-parse.js), and matching / recording on the
// Worker (src/screens/import.js).
import {DatabaseSync} from 'node:sqlite';
import {readFileSync, readdirSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {parseIcs, icsDate, titleGuesses, readMail, perfDate, unwrap, splitPasted} from '../src/client/import-parse.js';
import {importScreens, calendarUrl, fetchCalendar, ICS_MAX} from '../src/screens/import.js';
import {titleKey} from '../src/screens/works.js';

// ------------------------------------------------------------------ calendar

const ICS = `BEGIN:VCALENDAR\r
VERSION:2.0\r
BEGIN:VEVENT\r
DTSTART;TZID=Asia/Tokyo:20240512T140000\r
SUMMARY:観劇 『ハード・プロブレム』\r
LOCATION:世田谷パブリックシアター\\, 東京都世田谷区\r
END:VEVENT\r
BEGIN:VEVENT\r
DTSTART:20231104T100000Z\r
SUMMARY:夜の果て@本多劇場\r
END:VEVENT\r
BEGIN:VEVENT\r
DTSTART;VALUE=DATE:20240101\r
SUMMARY:元日\r
END:VEVENT\r
BEGIN:VEVENT\r
DTSTART:20240105T010000Z\r
RRULE:FREQ=WEEKLY\r
SUMMARY:定例ミーティング\r
END:VEVENT\r
BEGIN:VEVENT\r
DTSTART:20240301T090000Z\r
SUMMARY:とても長い題名の公演で行の折り返しがあるもの\r
 の続き\r
END:VEVENT\r
END:VCALENDAR\r
`;

test('iCal: events with their day in Japan time, folded lines joined, repeating ones marked', () => {
  const ev = parseIcs(ICS);
  assert.deepEqual(ev.map(e => [e.summary, e.date, e.time, e.recurring]), [
    ['観劇 『ハード・プロブレム』', '2024-05-12', '14:00', false],
    ['夜の果て@本多劇場', '2023-11-04', '19:00', false],       // 10:00 UTC is 19:00 in Japan
    ['元日', '2024-01-01', '', false],
    ['定例ミーティング', '2024-01-05', '10:00', true],
    ['とても長い題名の公演で行の折り返しがあるものの続き', '2024-03-01', '18:00', false],
  ]);
  assert.equal(ev[0].location, '世田谷パブリックシアター, 東京都世田谷区');
  assert.deepEqual(icsDate('20231231T200000Z'), {date: '2024-01-01', time: '05:00'});
  assert.equal(icsDate('garbage'), null);
});

test('iCal: title guesses from what people write in their own calendar', () => {
  assert.deepEqual(titleGuesses('観劇 『ハード・プロブレム』'), ['ハード・プロブレム', '『ハード・プロブレム』', '観劇 『ハード・プロブレム』']);
  assert.deepEqual(titleGuesses('夜の果て@本多劇場'), ['夜の果て', '夜の果て@本多劇場']);
  assert.deepEqual(titleGuesses('【マチネ】舞台：夜の果て（本多劇場）'), ['夜の果て', '【マチネ】舞台：夜の果て（本多劇場）']);
  assert.deepEqual(titleGuesses('a'), []);
});

test('only Google Calendar iCal addresses are fetched, and the size is capped', async () => {
  const good = 'https://calendar.google.com/calendar/ical/someone%40gmail.com/private-0123456789abcdef0123456789abcdef/basic.ics';
  assert.equal(calendarUrl(good), good);
  assert.equal(calendarUrl(good.replace('https://', 'webcal://')), good);
  for (const bad of ['https://evil.example/basic.ics', 'http://calendar.google.com/calendar/ical/a%40b.com/public/basic.ics',
    'https://calendar.google.com.evil.example/calendar/ical/a%40b.com/public/basic.ics', good + '?x=1', good.replace('basic.ics', '../basic.ics'),
    'https://calendar.google.com/calendar/ical/a%40b.com/private-xyz/basic.ics', null, 42])
    assert.equal(calendarUrl(bad), '', String(bad));
  const asked = [];
  const fetcher = async (url, init) => { asked.push([url, init.redirect]); return new Response('BEGIN:VCALENDAR'); };
  const ok = await fetchCalendar(good, fetcher);
  assert.equal(ok.status, 200);
  assert.equal(await new Response(ok.body).text(), 'BEGIN:VCALENDAR');
  assert.deepEqual(asked, [[good, 'manual']]);                       // a redirect elsewhere is not followed
  assert.equal((await fetchCalendar('https://evil.example/x.ics', fetcher)).status, 400);
  assert.equal(asked.length, 1);
  assert.equal((await fetchCalendar(good, async () => new Response('', {status: 302, headers: {location: 'https://evil.example'}}))).status, 502);
  const big = await fetchCalendar(good, async () => new Response(new ReadableStream({pull(c) { c.enqueue(new Uint8Array(1024 * 1024)); }})));
  await assert.rejects(new Response(big.body).arrayBuffer());       // stops past ICS_MAX
  assert.ok(ICS_MAX <= 8 * 1024 * 1024);
});

// ------------------------------------------------------------------ mails

const PIA = `差出人: チケットぴあ <info@pia.co.jp>
件名: 【チケットぴあ】チケット購入確認
お申込日：2024/04/01 10:00
公演名：ハード・プロブレム
公演日：2024/05/12(日)
開演時刻：14:00
会場名：世田谷パブリックシアター(東京都)
お支払期限：2024/04/03`;
const LTIKE = `■公演タイトル　：夜の果て
■公演日　：2023/11/04(土)　19:00開　演
■会場名　：本多劇場`;
const OKEPI = `[公演名] 『夜の果て』
[公演日時] 2023年11月4日(土) 19:00開演
[劇場] 本多劇場`;
const TOHO = `■公演名
レ・ミゼラブル
■劇場
帝国劇場
■公演日時
2024年6月1日(土) 12:00開演`;
const GEKIDAN = `劇団の公式インターネット・チケットサービスをご利用いただきありがとうございます。
予約番号：AB12345
夜の果て★追加公演
2023年11月4日(土) 19:00開演
お支払い期限：2023年10月20日`;
const GENERIC = `この度は「マルチコピー機」での発券についてのご案内です。
ご購入日 2024/01/10
公演『ハード・プロブレム』
観劇日 2024/05/12 14:00開演`;

test('mails: one rule per ticket site, told by the sender or by the body itself', () => {
  assert.deepEqual(readMail({text: PIA}), {title: 'ハード・プロブレム', date: '2024-05-12', time: '14:00', venue: '世田谷パブリックシアター', site: 'ぴあ', date_unsure: false});
  assert.deepEqual(readMail({text: LTIKE}), {title: '夜の果て', date: '2023-11-04', time: '19:00', venue: '本多劇場', site: 'ローチケ', date_unsure: false});
  assert.equal(readMail({text: OKEPI}).title, '夜の果て');                     // 『』 around the whole title come off
  assert.equal(readMail({text: OKEPI}).site, 'おけぴ');
  assert.deepEqual(readMail({text: TOHO}), {title: 'レ・ミゼラブル', date: '2024-06-01', time: '12:00', venue: '帝国劇場', site: '東宝ナビザーブ', date_unsure: false});
  assert.deepEqual(readMail({text: GEKIDAN}), {title: '夜の果て', date: '2023-11-04', time: '19:00', venue: '', site: '劇団のチケットサービス', date_unsure: false});
  // Generic: not the 「マルチコピー機」 in the instructions, and the performance day, not the purchase day.
  assert.deepEqual(readMail({text: GENERIC}), {title: 'ハード・プロブレム', date: '2024-05-12', time: '14:00', venue: '', site: 'そのほか', date_unsure: false});
});

test('mails: pick-up notices, concerts and undated mails are set aside with a reason', () => {
  assert.match(readMail({subject: 'チケット受取完了のお知らせ', text: PIA}).skip, /受け取り/);
  assert.match(readMail({text: '公演名：〇〇 LIVE TOUR 2024\n公演日：2024/05/12'}).skip, /演劇ではなさそう/);
  assert.match(readMail({text: '『夜の果て』をご予約いただきました'}).skip, /公演日/);
  assert.match(readMail({text: 'こんにちは'}).skip, /公演名/);
  assert.equal(perfDate('購入日 2024/01/10\n'), '');
  assert.equal(unwrap('劇団『演目』'), '劇団『演目』');
  assert.equal(unwrap('『劇団『演目』』'), '劇団『演目』');
  assert.equal(splitPasted(`${PIA}\n\n差出人: ローチケ <a@l-tike.com>\n${LTIKE}`).length, 2);
});

// ------------------------------------------------------------------ matching and recording

function setup() {
  const sqlite = new DatabaseSync(':memory:');
  for (const f of readdirSync(new URL('../migrations/', import.meta.url)).filter(n => n.endsWith('.sql')).sort()) sqlite.exec(readFileSync(new URL(`../migrations/${f}`, import.meta.url), 'utf8'));
  const wrap = (sql, args = []) => ({bind(...v) { return wrap(sql, v); }, async first() { return sqlite.prepare(sql).get(...args) ?? null; }, async all() { return {results: sqlite.prepare(sql).all(...args)}; }, async run() { return sqlite.prepare(sql).run(...args); }, async execute() { return /^\s*SELECT/.test(sql) ? this.all() : this.run(); }});
  const db = {prepare: sql => wrap(sql), async batch(cs) { const r = []; for (const c of cs) r.push(await c.execute()); return r; }};
  const past = (sid, title, start, end, venue = '本多劇場') => sqlite.prepare("INSERT INTO past_stage(stage_id,title,tkey,start,end,venue,people) VALUES(?,?,?,?,?,?,'[]')")
    .run(sid, title, titleKey(title), start, end, venue);
  for (const u of ['u1', 'u2']) sqlite.prepare('INSERT INTO users(id,recovery_hash,created_at) VALUES(?,?,0)').run(u, u);
  past('100', 'ハード・プロブレム', '2024-05-01', '2024-05-26', '世田谷パブリックシアター');
  past('200', '夜の果て', '2023-11-01', '2023-11-12');
  past('201', '夜の果て', '2021-03-01', '2021-03-10');
  const ctx = {db, uid: 'u1', today: '2026-10-14', now: Date.parse('2026-10-14T00:00:00Z')};
  const act = (name, input, c = ctx) => importScreens.actions[name](input, c);
  return {sqlite, ctx, act};
}

test('matching: same title on a day inside exactly one run; nothing stored', async () => {
  const {sqlite, act} = setup();
  const got = await act('import_match', {items: [
    {guesses: titleGuesses('観劇 『ハード・プロブレム』'), date: '2024-05-12'},
    {guesses: ['夜の果て'], date: '2023-11-04'},
    {guesses: ['夜の果て'], date: '2022-01-01'},              // no run that day
    {guesses: ['歯医者'], date: '2024-05-12'},
  ]});
  assert.deepEqual(got.body.items.map(i => i.stage_id), ['100', '200', '', '']);
  assert.equal(got.body.items[0].title, 'ハード・プロブレム');
  assert.equal(got.body.items[0].recorded, false);
  assert.equal(sqlite.prepare('SELECT count(*) AS n FROM works').get().n, 0);
  await assert.rejects(act('import_match', {items: Array(21).fill({guesses: ['a'], date: '2024-01-01'})}), /20 件まで/);
});

test('recording: ticked rows become records once; a stage id the catalogue lacks is dropped; others untouched', async () => {
  const {sqlite, act, ctx} = setup();
  const first = await act('import_works', {items: [
    {title: 'ハード・プロブレム', date: '2024-05-12', time: '14:00', venue: '世田谷パブリックシアター', stage_id: '100'},
    {title: '知らない公演', date: '2024-02-02', stage_id: '999'},
    {title: '夜の果て', date: '2023-11-04'},                    // linked by autolink
    {title: '', date: '2024-01-01'},
  ]});
  assert.deepEqual([first.body.added, first.body.skipped], [3, 0]);
  const rows = sqlite.prepare('SELECT title, first_date, stage_id, time FROM works WHERE user_id=? ORDER BY first_date').all('u1').map(r => ({...r}));
  assert.deepEqual(rows, [
    {title: '夜の果て', first_date: '2023-11-04', stage_id: '200', time: ''},
    {title: '知らない公演', first_date: '2024-02-02', stage_id: null, time: ''},
    {title: 'ハード・プロブレム', first_date: '2024-05-12', stage_id: '100', time: '14:00'},
  ]);
  const again = await act('import_works', {items: [{title: 'ハード・プロブレム', date: '2024-05-12', stage_id: '100'}]});
  assert.deepEqual([again.body.added, again.body.skipped], [0, 1]);
  const seen = await act('import_match', {items: [{guesses: ['ハード・プロブレム'], date: '2024-05-12'}]});
  assert.equal(seen.body.items[0].recorded, true);
  const other = await act('import_match', {items: [{guesses: ['ハード・プロブレム'], date: '2024-05-12'}]}, {...ctx, uid: 'u2'});
  assert.equal(other.body.items[0].recorded, false);
});

// ------------------------------------------------------------------ Google カレンダー (one button)
import {authUrl, eventsOf, startOf, CAL_SCOPE} from '../src/client/calendar-google.js';

test('Google Calendar: consent address asks only to read, and comes back to this site', () => {
  const u = new URL(authUrl('123.apps.googleusercontent.com', 'https://app.taguri.workers.dev', 'abc'));
  assert.equal(u.origin + u.pathname, 'https://accounts.google.com/o/oauth2/v2/auth');
  assert.equal(u.searchParams.get('scope'), CAL_SCOPE);
  assert.equal(CAL_SCOPE, 'https://www.googleapis.com/auth/calendar.readonly');
  assert.equal(u.searchParams.get('redirect_uri'), 'https://app.taguri.workers.dev/oauth/calendar');
  assert.equal(u.searchParams.get('response_type'), 'token');
  assert.equal(u.searchParams.get('state'), 'abc');
});

test('Google Calendar: events in Japan time, without repeating, cancelled or untitled ones', () => {
  assert.deepEqual(startOf({dateTime: '2024-05-12T05:00:00Z'}), {date: '2024-05-12', time: '14:00'});
  assert.deepEqual(startOf({dateTime: '2024-05-12T14:00:00+09:00'}), {date: '2024-05-12', time: '14:00'});
  assert.deepEqual(startOf({date: '2024-01-01'}), {date: '2024-01-01', time: ''});
  const got = eventsOf([
    {summary: '観劇 『ハード・プロブレム』', start: {dateTime: '2024-05-12T14:00:00+09:00'}, location: '世田谷パブリックシアター'},
    {summary: '定例', start: {dateTime: '2024-05-13T10:00:00+09:00'}, recurringEventId: 'x'},
    {summary: '中止', start: {date: '2024-05-14'}, status: 'cancelled'},
    {start: {date: '2024-05-15'}},
  ]);
  assert.deepEqual(got, [{summary: '観劇 『ハード・プロブレム』', date: '2024-05-12', time: '14:00', location: '世田谷パブリックシアター', recurring: false}]);
});

test('the page Google returns to may talk only to the Calendar API, and the client id is public config', async () => {
  const {default: worker} = await import('../src/worker.js');
  const {sqlite, ctx} = setup();
  const env = {DB: ctx.db, FIREBASE_PROJECT_ID: 'p', FIREBASE_API_KEY: 'k', GOOGLE_CALENDAR_CLIENT_ID: '123.apps.googleusercontent.com',
    ASSETS: {fetch: () => new Response('<html>', {headers: {'content-type': 'text/html'}})}};
  const cfg = await (await worker.fetch(new Request('https://app.example/api/auth/config'), env)).json();
  assert.equal(cfg.calendarClientId, '123.apps.googleusercontent.com');
  // Signed out: sent to sign in first.
  assert.equal((await worker.fetch(new Request('https://app.example/oauth/calendar'), env)).status, 302);
  sqlite.prepare("INSERT INTO sessions(hash,user_id,expires_at,created_at) VALUES(?,?,?,?)").run(
    [...new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode('a'.repeat(64))))].map(b => b.toString(16).padStart(2, '0')).join(''), 'u1', 9e9, 0);
  const page = await worker.fetch(new Request('https://app.example/oauth/calendar', {headers: {cookie: 'taguri_session=' + 'a'.repeat(64)}}), env);
  assert.equal(page.status, 200);
  const csp = page.headers.get('content-security-policy');
  assert.match(csp, /connect-src https:\/\/www\.googleapis\.com;/);
  assert.match(csp, /script-src 'self';/);
  assert.equal(page.headers.get('referrer-policy'), 'no-referrer');
});
