// #94: 評価一覧に評価が 1 件も無いとき、行き止まりにせず次に押す先を出す（Python の _rate_empty_next と同じ形。
// 比べるのは screens.test.js の "empty screens"）。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {setup, step, signIn} from './screens/harness.js';

test('#94: the empty rate screen links to 観劇記録を追加, then to the unrated records', async () => {
  const {env, sqlite} = setup();
  try {
    const cookie = await signIn(env);
    const html = async () => (await step(env, cookie, {get: '/api/screen/rate'})).body.body_html;
    const none = await html();
    // 2026-10-24 から、イラスト付きの案内（起案者の指示「評価一覧の初期画面、おすすめと同じようにイラスト付きでページ説明を書いて」）
    assert.match(none, /<section class="card tips eguide">[\s\S]*?過去に観た舞台の評価一覧が表示されます。[\s\S]*?右上の\+ボタンまたは<a href="\/register\?t=__TAGURI_TOKEN__">こちら<\/a>。[\s\S]*?「購入済」にした公演は、公演日時をすぎると自動的に評価一覧ページに表示されます。/);
    assert.doesNotMatch(none, /empty-next/);
    for (const title of ['評価前の舞台いち', '評価前の舞台に'])
      assert.equal((await step(env, cookie, {post: '/api/add_work', body: {title, date: '2026-09-01'}})).status, 200);
    const two = await html();
    assert.match(two, /<a href="\/rate\/unrated\?t=__TAGURI_TOKEN__">未評価の記録に評価する（2件）<\/a>/);
    assert.match(two, /過去に観た舞台の評価一覧が表示されます。/);
  } finally { sqlite.close(); }
});

test('未評価が 0 件で評価は付いているときは、イラスト付きの感謝 (起案者 2026-10-24)', async () => {
  const {env, sqlite} = setup();
  try {
    const cookie = await signIn(env);
    const unrated = async () => (await step(env, cookie, {get: '/api/screen/unrated'})).body.body_html;
    // 記録も評価も無いときは、前のまま
    assert.match(await unrated(), /<p class="empty">評価が付いていない記録はありません。<\/p>/);
    const key = (await step(env, cookie, {post: '/api/add_work', body: {title: '観た舞台', date: '2026-09-01'}})).body.work_key;
    assert.equal((await step(env, cookie, {post: '/api/rate', body: {work_key: key, verdict: '5/5'}})).status, 200);
    const done = await unrated();
    assert.match(done, /<section class="card tips eguide">[\s\S]*?ご回答ありがとうございました！[\s\S]*?<svg class="tip-art"/);
    assert.doesNotMatch(done, /評価が付いていない記録はありません/);
  } finally { sqlite.close(); }
});
