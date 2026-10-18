// 観劇記録を追加（/api/screen/register）の説明が、実際の動きと合っていること。
// #91: 取り込みの読み方ごとに、端末で読むもの・サーバーを通るもの・保存するものを分けて書く。
// #92: 手入力の「探す」は保存済みの公演一覧から探す（その場で CoRich を探さない）。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {setup, step, signIn} from './screens/harness.js';

async function registerHtml() {
  const {env, sqlite} = setup();
  try {
    const cookie = await signIn(env);
    const got = await step(env, cookie, {get: '/api/screen/register'});
    assert.equal(got.status, 200);
    return got.body.body_html;
  } finally { sqlite.close(); }
}

test('#91: the private address is said to pass through the server; files stay on the device', async () => {
  const html = await registerHtml();
  assert.doesNotMatch(html, /読み取りはこの端末の中だけで行い、カレンダーやメールの中身はたぐりに送りません/);
  assert.match(html, /アドレスをたぐりのサーバーに送り、サーバーが Google からカレンダー全体を取ってきて/);
  assert.match(html, /id="imx-url"[^>]*aria-describedby="imx-url-note"/);
  assert.match(html, /id="imx-url-note">このアドレスはたぐりのサーバーを通ります（保存はしません）/);
  assert.match(html, /題名の候補と日付は、公演と照合するためにたぐりに送ります/);
});

test('#92: manual entry searches the saved catalogue, not CoRich on the spot', async () => {
  const html = await registerHtml();
  assert.doesNotMatch(html, /CoRichで検索|8 秒/);
  assert.match(html, /data-sug-web="1">[\s\S]*?公演一覧から探す<\/button>/);
  assert.match(html, /その場で外のサイト（CoRich など）は探しません/);
  assert.match(html, /次の更新で探してもらう/);
});
