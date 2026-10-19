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

test('single entry comes first; import and unwatched performances stay separate', async () => {
  const html = await registerHtml();
  assert.ok(html.indexOf('id="w-title"') < html.indexOf('data-import'));
  assert.ok(html.indexOf('id="sug"') < html.indexOf('id="w-date"'));
  assert.ok(html.indexOf('id="w-venue"') < html.indexOf('data-add-work'));
  assert.ok(html.indexOf('data-import') < html.indexOf('register-missed'));
  assert.match(html, /公演名だけでも保存できます/);
  assert.match(html, /data-add-work="1">[\s\S]*?観劇記録を保存<\/button>/);
  assert.match(html, /<details class="card register-missed"><summary>/);
  assert.doesNotMatch(html, /<details class="imx-src" open|メールに残らない分を手で|入口は3つ/);
  for (const id of ['w-title', 'w-date', 'w-time', 'w-venue', 'sug', 'imx-url', 'imx-ics', 'imx-text', 'imx-eml']) {
    assert.equal(html.split(`id="${id}"`).length - 1, 1, id);
  }
});

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
  assert.match(html, /data-register-search="1"[^>]*>[\s\S]*?詳細検索<\/button>/);
  assert.doesNotMatch(html, /data-sug-web|公演一覧から探す/);
  assert.doesNotMatch(html, /data-register-repeat|data-register-reset|同じ作品を続けて追加する|別の作品を追加/);
  assert.match(html, /その場で外のサイト（CoRich など）は探しません/);
  assert.match(html, /次の更新で探してもらう/);
});

// #95: 入力欄には常に見える名前（label）を付け、必須か任意かを書く。placeholder は例だけ
test('#95: inputs have visible labels with required/optional, placeholders are examples', async () => {
  const {env, sqlite} = setup();
  try {
    const cookie = await signIn(env);
    const html = async path => (await step(env, cookie, {get: path})).body.body_html;
    const reg = await html('/api/screen/register');
    const label = (id, name, req) => new RegExp(`<label class="fld" for="${id}"><span class="fl">${name}<small class="${req ? 'req">必須' : 'opt">任意'}</small></span><(?:input|select) id="${id}"`);
    assert.match(reg, label('w-title', '公演の題名', true));
    assert.match(reg, label('w-date', '観た日', false));
    assert.match(reg, label('w-time', '開演時刻', false));
    assert.match(reg, label('w-venue', '劇場', false));
    assert.match(reg, /id="w-title" type="text" placeholder="例：/);
    assert.match(reg, /id="w-venue" type="text" placeholder="例：/);
    for (const path of ['/api/screen/start', '/api/screen/favourites']) {
      const h = await html(path);
      assert.match(h, label('fav-kind', '種類', true), path);
      assert.match(h, label('fav-name', '名前', true), path);
      assert.match(h, /id="fav-name" type="text" placeholder="例：/, path);
    }
    const search = await html('/api/screen/search');
    assert.match(search, /<label class="fld" for="search-q"><span class="fl">人名・団体・題材・題名<small class="req">必須<\/small><\/span><input type="text" id="search-q" name="q"/);
  } finally { sqlite.close(); }
});



