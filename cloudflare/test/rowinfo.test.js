// 評価一覧・日記帳の 1 件に、つながった公演の団体・会場・作り手・あらすじを添える（screens/rowinfo.js）。
// 起案者の指示 2026-10-18「評価一覧や日記帳のカードもおすすめと揃えて」
import {execFileSync} from 'node:child_process';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {setup, step, signIn} from './screens/harness.js';
import {creditRows} from '../src/screens/rowinfo.js';

const FIXTURE = JSON.parse(execFileSync('python3', [new URL('./screens/recommend_fixture.py', import.meta.url).pathname], {encoding: 'utf8', maxBuffer: 64 << 20}));

test('credits are grouped by role in the card order, with roles only in the stage fields added', () => {
  const rows = creditRows([['出演', '俳優乙'], ['演出', '演出家丙'], ['出演', '俳優甲'], ['出演', '俳優乙'], ['#形式', 'ストレート']],
    {'作': '劇作家丁', '演出': '欄の演出家', '振付': '振付家庚、振付家辛'});
  assert.deepEqual(rows, [['作', ['劇作家丁']], ['演出', ['演出家丙']], ['出演', ['俳優乙', '俳優甲']], ['振付', ['振付家庚', '振付家辛']]]);
});

test('a linked record shows the group, venue, credits and synopsis on 評価一覧 and 日記帳', async () => {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  const a = await signIn(env);
  try {
    const key = (await step(env, a, {post: '/api/add_work', body: {title: '終わった舞台', date: '2026-08-05'}})).body.work_key;
    await step(env, a, {post: '/api/link_stage', body: {work_key: key, stage_id: '103'}});
    await step(env, a, {post: '/api/rate', body: {work_key: key, verdict: '◎'}});
    sqlite.prepare("INSERT INTO stage_override(stage_id,synopsis,themes,info,updated_at) VALUES('103','港町の下宿屋の物語。',NULL,NULL,'x')").run();
    for (const path of ['/api/screen/rate', '/api/screen/works']) {
      const h = (await step(env, a, {get: path})).body.body_html;
      const m = /<div class="rinfo" data-grp="([^"]*)" data-venue="([^"]*)" data-times="[^"]*"(?: data-(?:url|page)="[^"]*")?>([\s\S]*?)<!--\/rinfo--><\/div>/.exec(h);
      assert.ok(m, path);
      assert.ok(m[1] || m[2], `${path}: group or venue`);
      assert.match(m[3], /<div class="cr"><span class="cl">出演<\/span>/, path);
      assert.match(m[3], /<p class="txt">港町の下宿屋の物語。<\/p>/, path);
    }
    // つながりの無い手入力の記録には添えない（Python と同じ行のまま）
    await step(env, a, {post: '/api/add_work', body: {title: 'つながらない舞台', date: '2026-08-06'}});
    const un = (await step(env, a, {get: '/api/screen/unrated'})).body.body_html;
    const row = un.slice(un.indexOf('つながらない舞台') - 400, un.indexOf('つながらない舞台') + 400);
    assert.doesNotMatch(row, /class="rinfo"/);
  } finally { sqlite.close(); }
});
