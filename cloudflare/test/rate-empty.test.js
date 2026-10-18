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
    assert.match(none, /まだ評価が付いた記録はありません。/);
    assert.match(none, /<p class="empty-next">観た公演を記録すると、ここで評価できます。<a href="\/register\?t=__TAGURI_TOKEN__">観劇記録を追加<\/a><\/p>/);
    for (const title of ['評価前の舞台いち', '評価前の舞台に'])
      assert.equal((await step(env, cookie, {post: '/api/add_work', body: {title, date: '2026-09-01'}})).status, 200);
    const two = await html();
    assert.match(two, /<a href="\/rate\/unrated\?t=__TAGURI_TOKEN__">未評価の記録に評価する（2件）<\/a>/);
    assert.doesNotMatch(two, /観劇記録を追加/);
  } finally { sqlite.close(); }
});
