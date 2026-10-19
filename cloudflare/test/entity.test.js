// おすすめ理由の太字（人物・形式）の個別の画面（起案者の指示 2026-10-19「おすすめ理由になってる項目の黒太字押したら、各個別ページに飛ぶように
// して。たとえば出演者なら飛んだ先に取得できる経歴やプロフィール、たぐり内にある過去の公演と今後の公演が見られる」、screens/entity.js）
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {setup, step, signIn} from './screens/harness.js';
import {reasonRows} from '../src/screens/recommend.js';

const here = p => new URL(p, import.meta.url).pathname;
const FIXTURE = JSON.parse(execFileSync('python3', [here('./screens/recommend_fixture.py')], {encoding: 'utf8', maxBuffer: 64 * 1024 * 1024}));

test('the bold names of the reasons link to the person and the kind pages', () => {
  const g = {parts: [[0, '出演', '俳優 乙', 2]], kinds: [[0, '#形式', 'ミュージカル', 2]]};
  const titles = new Map([['出演\t俳優 乙', ['舞台A']], ['#形式\tミュージカル', ['舞台A']]]);
  const html = reasonRows(g, titles);
  assert.match(html, /<a class="rsl" href="\/recommend\/person\?t=__TAGURI_TOKEN__&amp;n=%E4%BF%B3%E5%84%AA%20%E4%B9%99&amp;r=%E5%87%BA%E6%BC%94"><b>俳優 乙<\/b><\/a>/);
  assert.match(html, /<a class="rsl" href="\/recommend\/kind\?t=__TAGURI_TOKEN__&amp;a=%23%E5%BD%A2%E5%BC%8F&amp;w=%E3%83%9F%E3%83%A5%E3%83%BC%E3%82%B8%E3%82%AB%E3%83%AB"><b>ミュージカル<\/b><\/a>/);
});

test('the person page lists the coming stages, past stages, own records and outside links', async () => {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  sqlite.prepare("INSERT INTO past_stage(stage_id,title,tkey,start,end,venue,grp,pref,people) VALUES('9401','俳優乙の昔の舞台','俳優乙の昔の舞台','2022-05-01','2022-05-05','劇場Z','劇団Q','東京都','[]')").run();
  const a = await signIn(env);
  try {
    const r = await step(env, a, {get: '/api/screen/person?n=' + encodeURIComponent('俳優乙') + '&r=' + encodeURIComponent('出演')});
    assert.equal(r.status, 200);
    const h = r.body.body_html;
    assert.match(h, /<h1>俳優乙<\/h1>/);
    assert.match(h, /これから観られる公演 \d+ 件/);
    assert.match(h, /data-stage="10[12]"/);
    assert.match(h, /Wikipedia で調べる/);
    assert.match(h, /観た記録 \d+ 件/);
    assert.match(h, /過去の公演/);
    const k = await step(env, a, {get: '/api/screen/kind?a=' + encodeURIComponent('#形式') + '&w=' + encodeURIComponent('ミュージカル')});
    assert.equal(k.status, 200);
    assert.match(k.body.body_html, /<h1>形式「ミュージカル」の公演<\/h1>/);
    // 名前が無いときは案内だけ
    assert.match((await step(env, a, {get: '/api/screen/person'})).body.body_html, /名前がありません/);
  } finally { sqlite.close(); }
});
