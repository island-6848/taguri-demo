// 2026-10-19 の起案者の指示: お気に入りが 1 件も無いときはイラスト付きの案内（名前の欄の下）を出し、「すべて」の絞り込みを出さない
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {setup, step, signIn} from './screens/harness.js';

test('お気に入りが無いときは案内を出し、年月の絞り込み（すべて）・並べ替えは出さない', async () => {
  const {env, sqlite} = setup();
  const a = await signIn(env);
  try {
    const html = (await step(env, a, {get: '/api/screen/favourites'})).body.body_html;
    assert.match(html, /<section class="card tips eguide">[\s\S]*お気に入りに登録されている要素がありません。/);
    assert.ok(html.indexOf('id="fav-name"') < html.indexOf('eguide'), '案内は名前の欄の下');
    assert.doesNotMatch(html, /すべて|並べ替え/);
    await step(env, a, {post: '/api/favourite', body: {action: 'add', kind: '人', name: '俳優甲'}});
    assert.doesNotMatch((await step(env, a, {get: '/api/screen/favourites'})).body.body_html, /eguide/);
  } finally { sqlite.close(); }
});
