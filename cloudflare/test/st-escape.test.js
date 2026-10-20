// システムテスト SC-04-01（docs/system-test-spec.md、S14）: 利用者が入れた文字が、どの画面でも
// HTML として動かない。題名・劇場・感想・表示名・お気に入りの名前・修正依頼に TD-05 の文字列を入れ、
// Worker が答える全画面（/api/screen/*）と書き出しに、素のまま出ないことを見る。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {setup, signIn, step} from './screens/harness.js';
import {tickerScreens} from '../src/screens/ticker.js';
import {rateScreens} from '../src/screens/rate.js';
import {diaryScreens} from '../src/screens/diary.js';
import {accountScreens} from '../src/screens/account.js';
import {recommendScreens} from '../src/screens/recommend.js';
import {listScreens} from '../src/screens/lists.js';
import {reminderScreens} from '../src/screens/reminder.js';
import {calendarScreens} from '../src/screens/calendar.js';
import {settingsScreens} from '../src/screens/settings.js';
import {searchScreens} from '../src/screens/search.js';
import {taggedScreens} from '../src/screens/tagged.js';
import {entityScreens} from '../src/screens/entity.js';
import {recordScreens} from '../src/screens/records.js';

const SCREENS = Object.keys({...tickerScreens.screens, ...rateScreens.screens, ...diaryScreens.screens, ...accountScreens.screens,
  ...recommendScreens.screens, ...listScreens.screens, ...reminderScreens.screens, ...calendarScreens.screens, ...settingsScreens.screens,
  ...searchScreens.screens, ...taggedScreens.screens, ...entityScreens.screens, ...recordScreens.screens});

// TD-05。素のまま出てはいけない形（エスケープされていれば &lt; などになる）
const PAYLOADS = ['<script>alert(1)</script>', '"><img src=x onerror=alert(1)>', '</textarea><b>st</b>'];
const RAW = [/<script>alert\(1\)<\/script>/, /<img src=x onerror=alert\(1\)>/, /<\/textarea><b>st<\/b>/];
const JS_URL = /(?:href|src|action)\s*=\s*["']?\s*javascript:/i;

test('SC-04-01: TD-05 は全画面と書き出しで文字として出る', async () => {
  const {env} = setup();
  const a = await signIn(env);
  const p = (i) => PAYLOADS[i % PAYLOADS.length];
  for (let i = 0; i < PAYLOADS.length; i++) {
    const added = await step(env, a, {post: '/api/add_work', body: {title: `題${i}${p(i)}`, date: `2026-08-0${i + 1}`, venue: `劇場${p(i)}`}});
    assert.equal(added.status, 200, JSON.stringify(added.body));
    const key = added.body.work_key;
    assert.equal((await step(env, a, {post: '/api/rate', body: {work_key: key, verdict: '◎'}})).status, 200);
    assert.equal((await step(env, a, {post: '/api/note', body: {work_key: key, note_impression: `感想${p(i)} javascript:alert(1)`}})).status, 200);
  }
  await step(env, a, {post: '/api/favourite', body: {action: 'add', kind: '人', name: `俳優${p(0)}`}});
  await step(env, a, {post: '/api/account', body: {display_name: p(1).slice(0, 30)}});
  await step(env, a, {post: '/api/fix_request', body: {stage_id: '101', kind: '料金', message: `直して${p(2)}`}});

  const seen = [];
  for (const name of SCREENS) {
    const got = await step(env, a, {get: `/api/screen/${name}`});
    const text = typeof got.body === 'string' ? got.body : JSON.stringify(got.body);
    const html = typeof got.body === 'object' && got.body ? String(got.body.body_html ?? '') : text;
    for (const raw of RAW) assert.doesNotMatch(html, raw, `${name} に素のまま出た`);
    assert.doesNotMatch(html, JS_URL, `${name} に javascript: のリンクが出た`);
    if (got.status === 200) seen.push(name);
  }
  // 画面の引数に入れた文字（検索の語・人の名前）も同じ
  for (const raw of PAYLOADS) for (const path of [`/api/screen/search?q=${encodeURIComponent(raw)}`, `/api/screen/person?n=${encodeURIComponent(raw)}`]) {
    const got = await step(env, a, {get: path});
    const html = typeof got.body === 'object' && got.body ? String(got.body.body_html ?? '') : String(got.body);
    for (const r of RAW) assert.doesNotMatch(html, r, `${path} に素のまま出た`);
  }
  // 入れた文字が実際に画面に出ていること（出ていなければ、この試験は何も確かめていない）
  const records = await step(env, a, {get: '/api/screen/works'});
  assert.match(String(records.body.body_html), /&lt;script&gt;|&lt;img|&lt;\/textarea&gt;/, '記録の画面にエスケープした形で出る');
  assert.ok(seen.length >= 10, `開けた画面が少ない: ${seen.join(',')}`);
  if (process.env.ST_VERBOSE) console.log(SCREENS.length, seen.join(','));

  const exported = await step(env, a, {get: '/export.json'});
  if (exported.status === 200) {
    // 書き出しは JSON。値として入っていてよいが、HTML として返していないこと
    assert.equal(typeof exported.body, 'object', '書き出しは JSON で返す');
  }
});
