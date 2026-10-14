// Reading past events with the Google Calendar API, in the browser, with an access
// token for calendar.readonly (no token or event is sent to たぐり's server).
export const CAL_STATE_KEY = 'taguri_cal_state';
export const CAL_EVENTS_KEY = 'taguri_cal_events';
export const CAL_SCOPE = 'https://www.googleapis.com/auth/calendar.readonly';
const API = 'https://www.googleapis.com/calendar/v3';
const YEARS = 5;            // how far back to look
const MAX_EVENTS = 5000;    // what is handed over (sessionStorage is about 5 MB)
const MAX_PAGES = 10;       // per calendar, 2500 events a page

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

/** Past events of the calendars the user has (holiday and other subscribed calendars left out). */
export async function googleEvents(token, today, progress = () => {}) {
  const lists = await get(token, '/users/me/calendarList', {minAccessRole: 'writer', fields: 'items(id)'});
  const ids = (lists.items || []).map(c => c.id).filter(Boolean);
  const from = new Date(Date.parse(today + 'T00:00:00+09:00') - YEARS * 365 * 86400e3).toISOString();
  const to = new Date(Date.parse(today + 'T23:59:59+09:00')).toISOString();
  const out = [];
  for (const id of ids.length ? ids : ['primary']) {
    let pageToken = '';
    for (let page = 0; page < MAX_PAGES && out.length < MAX_EVENTS; page++) {
      const q = {timeMin: from, timeMax: to, singleEvents: 'true', orderBy: 'startTime', maxResults: '2500',
        fields: 'items(summary,start,location,status,recurringEventId),nextPageToken'};
      if (pageToken) q.pageToken = pageToken;
      const got = await get(token, `/calendars/${encodeURIComponent(id)}/events`, q);
      out.push(...eventsOf(got.items));
      progress(out.length);
      if (!got.nextPageToken) break;
      pageToken = got.nextPageToken;
    }
  }
  return out.slice(-MAX_EVENTS);
}
