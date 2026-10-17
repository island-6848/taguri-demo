// おすすめ画面の「おすすめに出てこない公演を探す」（起案者の指示 2026-10-17「でないときは探す、みたいにおすすめ画面に一個専用検索の検索バー置いて」）。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {setup, step, signIn} from './screens/harness.js';

const here = p => new URL(p, import.meta.url).pathname;
const FIXTURE = JSON.parse(execFileSync('python3', [here('./screens/recommend_fixture.py')], {encoding: 'utf8', maxBuffer: 64 * 1024 * 1024}));

test('a new user with no recommendations can find a stage on the recommend screen and answer 興味あり there', async () => {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  const a = await signIn(env);
  try {
    const empty = (await step(env, a, {get: '/api/screen/recommend'})).body.body_html;
    assert.match(empty, /今週のおすすめはありません/);
    assert.match(empty, /<section class="card rfind">[\s\S]*<form class="fav-add rfind-form" method="get" action="\/recommend">[\s\S]*name="find"/);
    const found = (await step(env, a, {get: '/api/screen/recommend?find=' + encodeURIComponent('ひとつめ')})).body.body_html;
    assert.match(found, /<section class="card rfind" id="rfind">[\s\S]*<h3>これから観られる公演 1 件<\/h3>/);
    assert.match(found, /<article class="ticket recommend" data-stage="101"/);
    const none = (await step(env, a, {get: '/api/screen/recommend?find=' + encodeURIComponent('存在しない題名')})).body.body_html;
    assert.match(none, /これから観られる公演には「存在しない題名」が見つかりませんでした/);
  } finally { sqlite.close(); }
});
