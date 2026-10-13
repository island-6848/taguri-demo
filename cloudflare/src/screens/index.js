// The original screens (/api/screen/*) and their writes (POST /api/*), answered
// by the Worker from D1 instead of Render. Each screen is a port of the Python
// function named next to it and must return the same body_html
// (test/screens.test.js runs the same steps on both).
//
// Enabled per name with env.NATIVE_UI ("all", or a comma list like
// "screen:rate,api:rate"); everything else still goes to Render until the
// switch-over (docs/render-migration-plan.md).
import {rateScreens} from './rate.js';

export const SCREEN_TABLES = ['works', 'excluded', 'merges', 'hand_credits', 'visit_note', 'reaction', 'viewed',
  'ticket', 'missed', 'rank_weight', 'app_setting', 'search_request'];
// Stands in for the Python server's per-process token (__TAGURI_TOKEN__). The
// public service never checks it; screens only carry it in links.
export const TOKEN = 'cfw0000000000000000000000000000000';

const SCREENS = {...rateScreens.screens};
const ACTIONS = {...rateScreens.actions};

const enabled = (env, kind, name) => {
  const list = String(env.NATIVE_UI || '').split(',').map(s => s.trim());
  return list.includes('all') || list.includes(`${kind}:${name}`);
};
export const nativeScreen = (env, name) => Object.hasOwn(SCREENS, name) && enabled(env, 'screen', name);
export const nativeAction = (env, name) => Object.hasOwn(ACTIONS, name) && enabled(env, 'api', name);

/** What Handler._json adds to every answer (public service edition). */
const envelope = obj => ({...obj, demo_mode: false, public: true, edition: 'service'});
const withToken = obj => JSON.parse(JSON.stringify(obj).replaceAll('__TAGURI_TOKEN__', TOKEN));

export async function screen(name, params, ctx) {
  const out = await SCREENS[name](params, ctx);
  return withToken(envelope({ok: true, ...out}));
}

export async function action(name, input, ctx) {
  const out = await ACTIONS[name](input, ctx);
  return {status: out.status || 200, body: withToken(envelope(out.body))};
}
