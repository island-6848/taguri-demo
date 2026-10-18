// お気に入りの人を役職で絞る（起案者の指示 2026-10-18「お気に入りの加藤拓也、同姓同名が2人いるみたいでどっちも拾っちゃう」
// →「Aで。ただし人って選んだあとに、細く指定したい場合のみ任意で選べるように。複数役職やる人もいるので」、q-favourite-homonym）
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {setup, step, signIn} from './screens/harness.js';
import {roleFits, rolesAllowed, favRoleBox, FAV_ROLES} from '../src/screens/lists.js';

const here = p => new URL(p, import.meta.url).pathname;
const FIXTURE = JSON.parse(execFileSync('python3', [here('./screens/recommend_fixture.py')], {encoding: 'utf8', maxBuffer: 64 * 1024 * 1024}));
async function withUser(fn) {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  const a = await signIn(env);
  try { await fn(env, a, sqlite); } finally { sqlite.close(); }
}
const add = (env, a, name, roles) => step(env, a, {post: '/api/favourite', body: {action: 'add', kind: '人', name, ...(roles ? {roles} : {})}});
const screen = async (env, a, name) => (await step(env, a, {get: '/api/screen/' + name})).body;

test('役職の札: 「作・演出」も演出・脚本に当たり、札が無ければどの役職でも当てる', () => {
  assert.equal(roleFits('出演', null), true);
  assert.equal(roleFits('作・演出', rolesAllowed(['演出'])), true);
  assert.equal(roleFits('出演', rolesAllowed(['脚本', '演出'])), false);
  assert.equal(rolesAllowed([]), null);
  assert.deepEqual(FAV_ROLES.map(([l]) => l), ['出演', '脚本', '演出', '作曲・音楽', '振付', '翻訳', '原作']);
  assert.match(favRoleBox(), /役職で絞る<small class="opt">任意<\/small>/);
});

test('a 人 narrowed to a role they do not have on a stage does not pick that stage, nor seed from it', async () => withUser(async (env, a, sqlite) => {
  const r = await add(env, a, '俳優甲', ['脚本', '演出']);
  assert.equal(r.status, 200);
  assert.deepEqual(r.body.roles, ['脚本', '演出']);
  assert.match(r.body.said, /脚本・演出として出ている公演だけ/);
  const fav = await screen(env, a, 'favourites');
  assert.doesNotMatch(fav.body_html, /data-stage="101"/);
  assert.match(fav.body_html, /#人「俳優甲」<small class="frole">脚本・演出<\/small>/);
  assert.match(fav.body_html, /<fieldset class="fav-roles">/);
  assert.equal((await screen(env, a, 'recommend')).diag.favourite_seeds, 0);
  // 出演に絞り直すと出る（足し直すと札を置き換える）
  await add(env, a, '俳優甲', ['出演']);
  assert.match((await screen(env, a, 'favourites')).body_html, /data-stage="101"/);
  // 札なしで足し直すと絞りが外れ、外すと控えも消える
  await add(env, a, '俳優甲');
  assert.equal(JSON.parse(sqlite.prepare("SELECT value FROM app_setting WHERE key='declared_roles'").get().value)['俳優甲'], undefined);
  await add(env, a, '俳優甲', ['出演']);
  await step(env, a, {post: '/api/favourite', body: {action: 'remove', kind: '人', name: '俳優甲'}});
  assert.equal(JSON.parse(sqlite.prepare("SELECT value FROM app_setting WHERE key='declared_roles'").get().value)['俳優甲'], undefined);
}));

test('unknown role labels are dropped, and no roles keeps the old behaviour', async () => withUser(async (env, a) => {
  const r = await add(env, a, '俳優甲', ['悪役', '<b>']);
  assert.equal(r.body.roles, undefined);
  assert.match((await screen(env, a, 'favourites')).body_html, /data-stage="101"/);
  assert.equal((await screen(env, a, 'recommend')).diag.favourite_seeds, 2);
}));
