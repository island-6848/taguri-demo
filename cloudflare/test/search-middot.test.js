// 点（・）を含む題名は、点を除いて打っても当たる（起案者の指示 2026-10-24「正式名称はミス・サイゴンだけど点を含む作品名は、
// ミスサイゴンのように点を除いても検索にヒットするようにして」）。逆に点を入れて打っても、点の無い題名に当たる
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {setup, step, signIn} from './screens/harness.js';

const here = p => new URL(p, import.meta.url).pathname;
const FIXTURE = JSON.parse(execFileSync('python3', [here('./screens/recommend_fixture.py')], {encoding: 'utf8', maxBuffer: 64 * 1024 * 1024}));
const search = (env, a, q) => step(env, a, {get: '/api/screen/search?q=' + encodeURIComponent(q)}).then(r => r.body.body_html);

test('a title with a middle dot is found without the dot, in the index, the catalogue, past stages and the records', async () => {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  const ver = sqlite.prepare("SELECT v FROM rec_meta WHERE k='current'").get().v;
  sqlite.prepare('INSERT INTO rec_stage(ver,stage_id,title,start,end,entry) VALUES(?,?,?,?,?,?)')
    .run(ver, '880001', 'ミュージカル『ミス・サイゴン』', '2099-05-01', '2099-06-30', JSON.stringify({title: 'ミュージカル『ミス・サイゴン』', theater: '帝国劇場', group: '東宝', fields: {'出演': 'チェ・ウヒョク'}}));
  sqlite.prepare('INSERT INTO catalogue(id,title,date,venue,url,metadata) VALUES(?,?,?,?,?,?)')
    .run('990002', 'メイユール・ソワレ', '2099-12-01', '博品館劇場', '', JSON.stringify({end_date: '2099-12-31', group: '劇団新'}));
  sqlite.prepare("INSERT INTO past_stage(stage_id,title,tkey,start,end,venue,grp,pref,people) VALUES('770001','ミス・サイゴン','ミスサイゴン','2022-08-01','2022-09-30','帝国劇場','東宝','東京都','[]')").run();
  const a = await signIn(env);
  try {
    await step(env, a, {post: '/api/add_work', body: {title: 'レ・ミゼラブル', date: '2025-06-01'}});
    const ms = await search(env, a, 'ミスサイゴン');
    assert.match(ms, /data-stage="880001"/, 'the index');
    assert.match(ms, /data-stage="770001" data-title="ミス・サイゴン"/, 'past stages');
    assert.match(await search(env, a, 'メイユールソワレ'), /data-stage="990002"/, 'the catalogue');
    assert.match(await search(env, a, 'レミゼラブル'), /レ・ミゼラブル/, 'the records');
    // 出演者の名前も同じ（点を除いて打っても当たる）
    assert.match(await search(env, a, 'チェウヒョク'), /data-stage="880001"/);
    // 観劇記録の追加の候補（題名の鍵は前から点を除いている）
    const sug = (await step(env, a, {get: '/api/suggest?q=' + encodeURIComponent('ミスサイゴン')})).body;
    assert.ok(sug.rows.some(r => r.stage_id === '770001'), JSON.stringify(sug.rows.map(r => r.title)));
    // 点を入れて打っても当たる
    assert.match(await search(env, a, 'ミス・サイゴン'), /data-stage="880001"/);
  } finally { sqlite.close(); }
});
