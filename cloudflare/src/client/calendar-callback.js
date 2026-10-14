// /oauth/calendar: where Google sends the user back after allowing たぐり to read
// their calendar (「公演情報の登録」①, Google カレンダーから). Bundled to
// public/vendor/calendar-callback.js by `npm run build:login`.
//
// The access token arrives in the address (#access_token=...). It is read here,
// in the browser, used to list the past events, and dropped: it never goes to
// たぐり's server and is not stored. Only the events (title, day, time, place)
// are handed to the 登録 screen through sessionStorage, which reads them once and
// matches them with the catalogue like an iCal file.
import {googleEvents, CAL_STATE_KEY, CAL_EVENTS_KEY} from './calendar-google.js';

const say = t => { document.getElementById('status').textContent = t; };
const params = new URLSearchParams(location.hash.slice(1));
history.replaceState(null, '', location.pathname);         // drop the token from the address
let expected = null;
try { expected = sessionStorage.getItem(CAL_STATE_KEY); sessionStorage.removeItem(CAL_STATE_KEY); } catch {}

async function run() {
  if (params.get('error')) { say(params.get('error') === 'access_denied' ? '取り込みを取りやめました。' : 'Google カレンダーを読めませんでした。'); return; }
  const token = params.get('access_token');
  // The state must be the one this browser made just before going to Google.
  if (!token || !expected || params.get('state') !== expected) { say('もう一度「Google カレンダーから取り込む」を押してください。'); return; }
  const today = new Date(Date.now() + 9 * 3600e3).toISOString().slice(0, 10);
  const events = await googleEvents(token, today, n => say(`予定を読んでいます… ${n} 件`));
  try { sessionStorage.setItem(CAL_EVENTS_KEY, JSON.stringify(events)); }
  catch { say('予定が多すぎて受け渡せませんでした。'); return; }
  location.replace('/register');
}
run().catch(() => say('Google カレンダーを読めませんでした。もう一度お試しください。'));
