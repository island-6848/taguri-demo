// カードの右上の ✕「候補から消す」（起案者の指示 2026-10-18「たとえばお気に入りとか、これいらんなってときがある。その時候補から
// 消したい。興味の画面でバツを押された場合は、興味なしか視界にも入れたくないから結構マイナスと判断できる」）。
// dismiss は reaction.interest=3（一覧から外すだけ）、興味ありの画面の dismiss_strong は 4（強い負の手がかり）
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {setup, step, signIn} from './screens/harness.js';
import {personValues, REJECT_W} from '../src/recommend.js';

const here = p => new URL(p, import.meta.url).pathname;
const FIXTURE = JSON.parse(execFileSync('python3', [here('./screens/recommend_fixture.py')], {encoding: 'utf8', maxBuffer: 64 * 1024 * 1024}));
async function withUser(fn) {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  const a = await signIn(env);
  try { await fn(env, a, sqlite); } finally { sqlite.close(); }
}
const screen = async (env, a, name) => (await step(env, a, {get: '/api/screen/' + name})).body.body_html;
const interestOf = (sqlite, sid) => sqlite.prepare('SELECT interest FROM reaction WHERE stage_id=? ORDER BY updated_at DESC').get(sid)?.interest;

test('✕ on a favourite\'s stage takes it off お気に入り and the recommendations', async () => withUser(async (env, a, sqlite) => {
  assert.equal((await step(env, a, {post: '/api/favourite', body: {action: 'add', kind: '人', name: '俳優甲'}})).status, 200);
  assert.match(await screen(env, a, 'favourites'), /data-stage="101"/);
  const r = await step(env, a, {post: '/api/react', body: {stage_id: '101', value: 'dismiss', from: 'favourites', nofill: true}});
  assert.equal(r.status, 200);
  assert.equal(interestOf(sqlite, '101'), 3);
  assert.doesNotMatch(await screen(env, a, 'favourites'), /data-stage="101"/);
  assert.doesNotMatch(await screen(env, a, 'recommend'), /data-stage="101"/);
  assert.doesNotMatch(await screen(env, a, 'interest'), /data-stage="101"/);
}));

test('✕ on 興味あり (dismiss_strong) takes it off the list and is kept as 4', async () => withUser(async (env, a, sqlite) => {
  await step(env, a, {post: '/api/react', body: {stage_id: '101', value: 'interest', nofill: true}});
  assert.match(await screen(env, a, 'interest'), /data-stage="101"/);
  assert.equal((await step(env, a, {post: '/api/react', body: {stage_id: '101', value: 'dismiss_strong', nofill: true}})).status, 200);
  assert.equal(interestOf(sqlite, '101'), 4);
  assert.doesNotMatch(await screen(env, a, 'interest'), /data-stage="101"/);
  assert.doesNotMatch(await screen(env, a, 'recommend'), /data-stage="101"/);
}));

test('an unknown value is still refused', async () => withUser(async (env, a) => {
  assert.equal((await step(env, a, {post: '/api/react', body: {stage_id: '101', value: 'nope', nofill: true}})).status, 400);
}));

test('a stage ✕-ed on 興味あり pulls its people down; a plain 興味なし does not on its own', () => {
  const liked = [{stage_id: 'L', people: [['出演', '好き'], ['出演', '共通']]}];
  const no = {stage_id: 'N', people: [['出演', '苦手'], ['出演', '共通']]};
  const val = (v, p) => (v.get('出演\u0000' + p) || [0, 0])[1];
  const plain = personValues([], [], new Set(), liked, [no]);
  assert.equal(val(plain, '苦手'), 0);
  const strong = personValues([], [], new Set(), liked, [{...no, strong: true}]);
  assert.ok(val(strong, '苦手') < 0, String(val(strong, '苦手')));
  // 好きな人と同じ公演にいた人は、好きの分と打ち消し合う
  assert.ok(val(strong, '共通') < val(plain, '共通'));
  assert.ok(val(strong, '好き') > 0);
  // ✕ だけでも負の値になる（興味ありが無くても）
  assert.ok(val(personValues([], [], new Set(), [], [{...no, strong: true}]), '苦手') < 0);
  assert.equal(REJECT_W, 1);
});
