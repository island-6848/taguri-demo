// #93: はじめる（/api/screen/start）は、いまの状態（何も無い／名前か記録だけ／評価した記録がある）で
// 見出しと次の一歩を変え、例はいまの評価の段階で出し、おすすめの材料をいまの決まりどおりに書く。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {setup, step, signIn} from './screens/harness.js';

test('#93: the start screen follows what the user has done, in their rating scale', async () => {
  const {env, sqlite} = setup();
  try {
    const cookie = await signIn(env);
    const html = async () => (await step(env, cookie, {get: '/api/screen/start'})).body.body_html;
    const empty = await html();
    assert.match(empty, /<h1>はじめに、見逃したくない名前を 1 つ登録してください<\/h1>/);
    assert.match(empty, /まだ登録も記録もない/);
    assert.match(empty, /どの画面もまだ0件です/);
    // 初期の段階は星 5 段階: ◎ ではなく ★ で書く
    assert.match(empty, /★5 を付けた公演の出演者・作り手は上がり/);
    assert.doesNotMatch(empty, /◎/);
    assert.match(empty, /お気に入りに登録した名前：観たことが無くても材料になり、<b>興味ありより強く効きます<\/b>/);

    assert.equal((await step(env, cookie, {post: '/api/favourite', body: {action: 'add', kind: '人', name: '甲'}})).status, 200);
    const fav = await html();
    assert.match(fav, /<h1>名前を登録しました。次は観た公演を評価してください<\/h1>/);
    assert.doesNotMatch(fav, /まだ登録も記録もない|どの画面もまだ0件/);
    assert.match(fav, /済んでいること：名前の登録（1 件）/);
    assert.match(fav, /お気に入りの公演を見る/);

    const add = await step(env, cookie, {post: '/api/add_work', body: {title: '観た舞台', date: '2026-09-01'}});
    assert.equal(add.status, 200);
    assert.match(await html(), /次は、未評価の記録 1 件に ★1〜★5 を付けてください/);
    assert.equal((await step(env, cookie, {post: '/api/rate', body: {work_key: add.body.work_key, verdict: '4/5'}})).status, 200);
    const rated = await html();
    assert.match(rated, /<h1>準備はできています<\/h1>/);
    assert.match(rated, /評価した記録 1 件と、登録した名前 1 件をもとに/);
    assert.match(rated, /今週のおすすめを見る/);

    // ◎○△× の段階を選んだ人には ◎ で書く
    assert.equal((await step(env, cookie, {post: '/api/rating_scale', body: {scale: 'marks4'}})).status, 200);
    assert.match(await html(), /◎ を付けた公演の出演者・作り手は上がり、× の公演の人は下がります/);
  } finally { sqlite.close(); }
});
