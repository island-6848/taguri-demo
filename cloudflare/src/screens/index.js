// The original screens (/api/screen/*) and their writes (POST /api/*), answered
// by the Worker from D1 instead of Render. Each screen is a port of the Python
// function named next to it and must return the same body_html
// (test/screens.test.js runs the same steps on both).
//
// Enabled per name with env.NATIVE_UI ("all", or a comma list like
// "screen:rate,api:rate"); everything else still goes to Render until the
// switch-over (docs/render-migration-plan.md).
import {rateScreens} from './rate.js';
import {diaryScreens} from './diary.js';
import {accountScreens} from './account.js';
import {ValueError} from './py.js';

export const SCREEN_TABLES = ['works', 'excluded', 'merges', 'hand_credits', 'visit_note', 'reaction', 'viewed',
  'ticket', 'missed', 'rank_weight', 'app_setting', 'search_request'];
// Stands in for the Python server's per-process token (__TAGURI_TOKEN__). The
// public service never checks it; screens only carry it in links.
export const TOKEN = 'cfw0000000000000000000000000000000';

const SCREENS = {...rateScreens.screens, ...diaryScreens.screens, ...accountScreens.screens};
const ACTIONS = {...rateScreens.actions, ...diaryScreens.actions, ...accountScreens.actions};

const enabled = (env, kind, name) => {
  const list = String(env.NATIVE_UI || '').split(',').map(s => s.trim());
  return list.includes('all') || list.includes(`${kind}:${name}`);
};
export const nativeScreen = (env, name) => Object.hasOwn(SCREENS, name) && enabled(env, 'screen', name);
export const nativeAction = (env, name) => Object.hasOwn(ACTIONS, name) && enabled(env, 'api', name);
/** NATIVE_UI=all: the Worker answers every screen; Render is no longer asked (q-native-cutover). */
export const allNative = env => String(env.NATIVE_UI || '').split(',').map(s => s.trim()).includes('all');

/** What Handler._json adds to every answer (public service edition). */
const envelope = obj => ({...obj, demo_mode: false, public: true, edition: 'service'});
const withToken = obj => JSON.parse(JSON.stringify(obj).replaceAll('__TAGURI_TOKEN__', TOKEN));

// Screens not ported yet, once production no longer goes to Render (NATIVE_UI=all).
// Their titles are the ones serve.py gives. 起案者の指示（2026-10-14）「本番用のサイトなはずなのに、
// デモ用の内容がでる。最初ログイン（会員登録）したらデータは空なはず」で、移し終える前に切り替えた。
const MOVING_TITLES = {recommend: '今週のおすすめ', reminder: '開幕リマインド', register: '公演情報の登録',
  interest: '興味あり', favourites: 'お気に入り', calendar: '公演カレンダー', tickets: '購入済み公演',
  records: '眺める', trace: 'たどる', chronicle: '観劇史年表', start: 'はじめる', settings: '設定', search: '探す'};
export function movingScreen(name) {
  const title = MOVING_TITLES[name] || 'この画面';
  const settings = name === 'settings'
    ? '<p class="lede">表示名・ログインの方法・ログアウト・アカウントの削除は、<a href="/account">アカウント</a>の画面にあります。</p>' : '';
  const body = `<h1>${title}</h1>${settings}
<p class="pnow">この画面は、いま新しい仕組みに移しています。移し終えたら、ここに表示されます。</p>
<p class="note">いま使えるのは、観た公演の<a href="/rate?t=__TAGURI_TOKEN__">評価一覧</a>・<a href="/rate/unrated?t=__TAGURI_TOKEN__">未評価</a>・<a href="/rate/notes?t=__TAGURI_TOKEN__">感想</a>・<a href="/records/works?t=__TAGURI_TOKEN__">日記帳</a>と、<a href="/account">アカウント</a>です。ここで記録したものは、移し終えた画面にもそのまま使われます。</p>`;
  return withToken(envelope({ok: true, title, body_html: body, moving: true}));
}
export const movingAction = () => ({status: 503, body: envelope({error: 'この操作は、いま新しい仕組みに移しているところです。移し終えるまでお待ちください'})});

export async function screen(name, params, ctx) {
  const out = await SCREENS[name](params, ctx);
  return withToken(envelope({ok: true, ...out}));
}

export async function action(name, input, ctx) {
  let out;
  try {
    out = await ACTIONS[name](input, ctx);
  } catch (error) {
    // do_POST: `except ValueError as e: self._json(400, {"error": str(e)})`
    if (!(error instanceof ValueError)) throw error;
    out = {status: 400, body: {error: error.message}};
  }
  return {status: out.status || 200, body: withToken(envelope(out.body))};
}

/**
 * The request body as do_POST reads it: at most 8 KB (Content-Length over the
 * cap is 413), an empty body is {}, anything but a JSON object is 400 "json".
 * Returns {input} or {status, body} (already wrapped like Handler._json).
 */
export async function readInput(request) {
  const cap = 8192;
  const declared = Number(request.headers.get('content-length') || 0);
  const tooLong = {status: 413, body: envelope({error: '本文の長さが不正です'})};
  if (!Number.isInteger(declared) || declared < 0) return {status: 400, body: tooLong.body};
  if (declared > cap) return tooLong;
  const bytes = new Uint8Array(await request.arrayBuffer());
  if (bytes.length > cap) return tooLong;
  try {
    const value = bytes.length ? JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(bytes)) : {};
    if (value && typeof value === 'object' && !Array.isArray(value)) return {input: value};
  } catch { /* fall through */ }
  return {status: 400, body: envelope({error: 'json'})};
}
