// Reading past events with the Google Calendar API, in the browser, with an access
// token for calendar.readonly (no token or event is sent to たぐり's server).
export const CAL_STATE_KEY = 'taguri_cal_state';
export const CAL_EVENTS_KEY = 'taguri_cal_events';
export const CAL_SCOPE = 'https://www.googleapis.com/auth/calendar.readonly';
const API = 'https://www.googleapis.com/calendar/v3';
const YEARS = 5;            // how far back to look
const MAX_EVENTS = 5000;    // what is handed over (sessionStorage is about 5 MB)
const PAGE = 2500;          // events a page (the API's largest)
const WINDOW_DAYS = 182;    // a calendar with more than a page is read again half a year at a time, newest first
const WINDOW_PAGES = 2;     // pages per span
const LIST_PAGES = 10;      // calendarList pages (250 calendars a page)

/** The address of Google's consent page; `state` is kept to check the way back. */
export function authUrl(clientId, origin, state) {
  const q = new URLSearchParams({client_id: clientId, redirect_uri: origin + '/oauth/calendar', response_type: 'token',
    scope: CAL_SCOPE, state, include_granted_scopes: 'true', prompt: 'select_account'});
  return 'https://accounts.google.com/o/oauth2/v2/auth?' + q;
}

const pad = n => String(n).padStart(2, '0');
/** An event's start in Japan time: {date, time}. */
export function startOf(start) {
  if (!start) return null;
  if (start.date) return {date: start.date, time: ''};
  const t = Date.parse(start.dateTime || '');
  if (Number.isNaN(t)) return null;
  const j = new Date(t + 9 * 3600e3);
  return {date: j.toISOString().slice(0, 10), time: `${pad(j.getUTCHours())}:${pad(j.getUTCMinutes())}`};
}

/** Google's events -> [{summary, date, time, location}] like parseIcs, leaving out repeating ones. */
export function eventsOf(items) {
  const out = [];
  for (const e of items || []) {
    if (e.recurringEventId || e.status === 'cancelled' || !e.summary) continue;
    const s = startOf(e.start);
    if (s) out.push({summary: String(e.summary).slice(0, 200), date: s.date, time: s.time, location: String(e.location || '').slice(0, 200), recurring: false});
  }
  return out;
}

async function get(token, path, params) {
  const res = await fetch(`${API}${path}?${new URLSearchParams(params)}`, {headers: {Authorization: `Bearer ${token}`}, referrerPolicy: 'no-referrer'});
  if (!res.ok) throw new Error(String(res.status));
  return res.json();
}

/** Every page of a list (calendarList, events), at most `max` pages: {items, more} (more: pages were left). */
export async function pages(fetchPage, max) {
  const items = [];
  let pageToken = '';
  for (let n = 0; n < max; n++) {
    const got = await fetchPage(pageToken);
    items.push(...(got.items || []));
    if (!got.nextPageToken) return {items, more: false};
    pageToken = got.nextPageToken;
  }
  return {items, more: true};
}

/**
 * How many of each calendar's events to keep when together they are more than `max`: an equal
 * share each, and what a small calendar does not use goes to the others (a busy work calendar
 * cannot push out a private one). [count...] -> [kept...].
 */
export function shares(counts, max) {
  const out = counts.map(() => 0);
  let left = max;
  const order = counts.map((_, i) => i).sort((a, b) => counts[a] - counts[b]);
  order.forEach((i, k) => { out[i] = Math.min(counts[i], Math.floor(left / (order.length - k))); left -= out[i]; });
  return out;
}

const newestFirst = (a, b) => (b.date + b.time).localeCompare(a.date + a.time);

/**
 * Past events of the calendars the user has (holiday and other subscribed calendars left out):
 * {events, capped, since}. When there are too many, the newer ones are kept: a calendar with
 * more than a page in the 5 years is read again from today backwards half a year (or less) at a time,
 * and when the calendars together hold more than MAX_EVENTS, each keeps its newest share.
 * capped says older events were left out, and since is the oldest day kept, for the screen to
 * tell. Requests stay few: one per calendar in the usual case (this runs on the user's quota).
 */
export async function googleEvents(token, today, progress = () => {}) {
  const lists = await pages(pageToken => get(token, '/users/me/calendarList',
    {minAccessRole: 'writer', maxResults: '250', fields: 'items(id),nextPageToken', ...(pageToken ? {pageToken} : {})}), LIST_PAGES);
  const ids = [...new Set(lists.items.map(c => c.id).filter(Boolean))];
  const from = new Date(Date.parse(today + 'T00:00:00+09:00') - YEARS * 365 * 86400e3).toISOString();
  const to = new Date(Date.parse(today + 'T23:59:59+09:00')).toISOString();
  const read = (id, timeMin, timeMax, max) => pages(pageToken => get(token, `/calendars/${encodeURIComponent(id)}/events`, {
    timeMin, timeMax, singleEvents: 'true', orderBy: 'startTime', maxResults: String(PAGE),
    fields: 'items(summary,start,location,status,recurringEventId),nextPageToken', ...(pageToken ? {pageToken} : {})}), max);
  let capped = lists.more, total = 0;
  const per = [];
  for (const id of ids.length ? ids : ['primary']) {
    let got = await read(id, from, to, 1);
    let events = eventsOf(got.items);
    if (got.more) {
      // More than a page (the API gives the oldest first): newest half year first, until this
      // calendar alone fills the limit.
      // A span with still more than WINDOW_PAGES is read again a quarter as long, from the same end.
      events = [];
      let span = WINDOW_DAYS * 86400e3;
      for (let end = Date.parse(to), lo = Date.parse(from); end > lo;) {
        if (events.length >= MAX_EVENTS) { capped = true; break; }
        const start = Math.max(lo, end - span);
        got = await read(id, new Date(start).toISOString(), new Date(end).toISOString(), WINDOW_PAGES);
        if (got.more && span > 86400e3) { span = Math.max(86400e3, span / 4); continue; }
        if (got.more) capped = true;
        events.push(...eventsOf(got.items));
        progress(total + events.length);
        end = start;
      }
    }
    per.push(events.sort(newestFirst));
    total += events.length;
    progress(total);
  }
  const keep = shares(per.map(e => e.length), MAX_EVENTS);
  if (keep.some((k, i) => k < per[i].length)) capped = true;
  const events = per.flatMap((e, i) => e.slice(0, keep[i]));
  const since = capped && events.length ? events.reduce((a, e) => (e.date < a ? e.date : a), today) : '';
  return {events, capped, since};
}
