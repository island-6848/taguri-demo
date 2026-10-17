// 推薦を本番の利用者のデータで測るための記録（起案者の指示 2026-10-17「1も2もお願い」、real-data-eval-plan §5・§7）。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {setup, step, signIn} from './screens/harness.js';
import {personValues} from '../src/recommend.js';

const here = p => new URL(p, import.meta.url).pathname;
const FIXTURE = JSON.parse(execFileSync('python3', [here('./screens/recommend_fixture.py')], {encoding: 'utf8', maxBuffer: 64 * 1024 * 1024}));

async function rated(env, a) {
  for (const [title, date, sid, verdict] of [['終わった舞台', '2026-08-05', '103', '◎'], ['一日だけの舞台', '2026-09-05', '104', '×']]) {
    const key = (await step(env, a, {post: '/api/add_work', body: {title, date}})).body.work_key;
    await step(env, a, {post: '/api/link_stage', body: {work_key: key, stage_id: sid}});
    await step(env, a, {post: '/api/rate', body: {work_key: key, verdict}});
  }
}

test('an answer keeps its rank, score and version in the same row, and the day keeps what was shown', async () => {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  const a = await signIn(env);
  try {
    await rated(env, a);
    assert.match((await step(env, a, {get: '/api/screen/recommend'})).body.body_html, /data-stage="101"/);
    const shown = sqlite.prepare("SELECT ids, ver FROM rec_shown WHERE screen='recommend'").all();
    assert.equal(shown.length, 1);
    assert.ok(JSON.parse(shown[0].ids).includes('101'));
    assert.match(shown[0].ver, /^screen-v\d+\|/);
    // 開き直しても、新しく出した公演が無ければ書かない（行は 1 つのまま、更新日時も同じ）
    const at = sqlite.prepare('SELECT updated_at FROM rec_shown').get().updated_at;
    await step(env, a, {get: '/api/screen/recommend'});
    assert.equal(sqlite.prepare('SELECT count(*) AS n, max(updated_at) AS at FROM rec_shown').get().at, at);
    await step(env, a, {post: '/api/react', body: {stage_id: '101', value: 'interest', nofill: true}});
    const r = sqlite.prepare("SELECT rank, score, ver, arm FROM reaction WHERE stage_id='101'").get();
    assert.equal(r.rank, 1);
    assert.equal(typeof r.score, 'number');
    assert.match(r.ver, /^screen-v\d+\|/);
    assert.equal(r.arm, null);
    // 書き直しは 1 日 6 回まで（無料枠）
    sqlite.prepare("UPDATE rec_shown SET writes=6, ids='[]'").run();
    await step(env, a, {get: '/api/screen/recommend'});
    assert.equal(sqlite.prepare('SELECT ids FROM rec_shown').get().ids, '[]');
    // 理由だけを書き足しても、順位は消えない
    await step(env, a, {post: '/api/react', body: {stage_id: '101', note: 'メモ'}});
    assert.equal(sqlite.prepare("SELECT rank FROM reaction WHERE stage_id='101'").get().rank, 1);
  } finally { sqlite.close(); }
});

test('old rows go after 180 days, and 分析に使わない stops both records and clears what was kept', async () => {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  const a = await signIn(env);
  try {
    await rated(env, a);
    const uid = sqlite.prepare('SELECT id FROM users').get().id;
    sqlite.prepare("INSERT INTO rec_shown(user_id,label,screen,ids,updated_at) VALUES(?, '2020-01-01', 'recommend', '[\"9\"]', 'x')").run(uid);
    await step(env, a, {get: '/api/screen/recommend'});
    assert.deepEqual(sqlite.prepare('SELECT label FROM rec_shown').all().map(r => r.label).includes('2020-01-01'), false);
    assert.match((await step(env, a, {get: '/api/screen/settings'})).body.body_html, /推薦の改善の分析に使わない/);
    assert.equal((await step(env, a, {post: '/api/analysis_optout', body: {off: true}})).status, 200);
    assert.equal(sqlite.prepare('SELECT count(*) AS n FROM rec_shown').get().n, 0);
    await step(env, a, {get: '/api/screen/recommend'});
    await step(env, a, {get: '/api/screen/reminder'});
    assert.equal(sqlite.prepare('SELECT count(*) AS n FROM rec_shown').get().n, 0);
    await step(env, a, {post: '/api/react', body: {stage_id: '101', value: 'interest', nofill: true}});
    const r = sqlite.prepare("SELECT interest, rank, ver FROM reaction WHERE stage_id='101'").get();
    assert.deepEqual([r.interest, r.rank, r.ver], [1, null, null]);
    assert.equal((await step(env, a, {post: '/api/analysis_optout', body: {off: 'yes'}})).status, 400);
  } finally { sqlite.close(); }
});

test('the ablation flag changes nothing by default and evens the interest split when asked', () => {
  const liked = [{people: [['演出', 'A'], ['出演', 'B'], ['出演', 'C']], cast_text: 'B\nアンサンブル\nC'}];
  const base = personValues([], [], new Set(), liked, []);
  assert.deepEqual(personValues([], [], new Set(), liked, [], {}), base);
  const even = personValues([], [], new Set(), liked, [], {split: true});
  const v = k => even.get(k)[1];
  assert.ok(Math.abs(v('出演\u0000B') - v('出演\u0000C')) < 1e-12);
  assert.ok(base.get('出演\u0000B')[1] > base.get('出演\u0000C')[1]);
});
