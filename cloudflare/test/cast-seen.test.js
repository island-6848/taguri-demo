// 観た回の出演者（起案者の指示 2026-10-15「Wキャストの出演者を選べるようにして」）: 記録ごとに、
// 観た回に出ていなかった出演者を外すと、推薦はその人をこの記録の材料にしない。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {setup, step, signIn} from './screens/harness.js';

const here = p => new URL(p, import.meta.url).pathname;
const FIXTURE = JSON.parse(execFileSync('python3', [here('./screens/recommend_fixture.py')], {encoding: 'utf8', maxBuffer: 64 * 1024 * 1024}));
function withIndex() {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  return {env, sqlite};
}
async function rateSeen(env, u, title, date, sid, verdict) {
  const key = (await step(env, u, {post: '/api/add_work', body: {title, date}})).body.work_key;
  assert.equal((await step(env, u, {post: '/api/link_stage', body: {work_key: key, stage_id: sid}})).status, 200);
  assert.equal((await step(env, u, {post: '/api/rate', body: {work_key: key, verdict}})).status, 200);
  return key;
}
const recommend = async (env, u) => (await step(env, u, {get: '/api/screen/recommend'})).body.body_html;

test('a W-cast performer who was not on stage that night stops counting for the recommendations', async () => {
  const {env, sqlite} = withIndex();
  const a = await signIn(env), b = await signIn(env);
  try {
    // 103 has 俳優甲 only; 101 (coming) has 俳優乙 and 俳優甲.
    const seen = await rateSeen(env, a, '終わった舞台', '2026-08-05', '103', '◎');
    await rateSeen(env, a, '一日だけの舞台', '2026-09-05', '104', '×');
    assert.match(await recommend(env, a), /data-stage="101"/);
    // The editor offers the choice for a linked record.
    assert.match((await step(env, a, {get: '/api/screen/works'})).body.body_html, /data-cast-open="[^"]+">Wキャスト・休演で出ていなかった人を選ぶ/);
    const got = await step(env, a, {post: '/api/cast_seen', body: {work_key: seen}});
    assert.deepEqual([got.status, got.body.cast, got.body.off], [200, ['俳優甲'], []]);
    // Every performer off is refused: at least one must stay.
    assert.equal((await step(env, a, {post: '/api/cast_seen', body: {work_key: seen, off: ['俳優甲']}})).status, 400);
    // A name that is not in the cast, or someone else's record, is refused.
    assert.equal((await step(env, a, {post: '/api/cast_seen', body: {work_key: seen, off: ['だれか']}})).status, 400);
    assert.equal((await step(env, b, {post: '/api/cast_seen', body: {work_key: seen}})).status, 400);
  } finally { sqlite.close(); }
});

test('off performers leave the record\'s material; relinking the record clears the choice', async () => {
  const {env, sqlite} = withIndex();
  const a = await signIn(env);
  try {
    // A ◎ on 101 (俳優乙・俳優甲) raises the coming 102 through 俳優乙.
    sqlite.exec("UPDATE rec_stage SET start='2026-12-01', end='2026-12-10' WHERE stage_id='102'");
    const k = await rateSeen(env, a, '舞台ひとつめ', '2026-08-01', '101', '◎');
    await rateSeen(env, a, '一日だけの舞台', '2026-09-05', '104', '×');
    const before = await recommend(env, a);
    assert.match(before, /data-stage="102"[\s\S]*?出演 <a class="rsl"[^>]*><b>俳優乙<\/b><\/a>/);
    assert.equal((await step(env, a, {post: '/api/cast_seen', body: {work_key: k, off: ['俳優乙']}})).status, 200);
    assert.equal(sqlite.prepare('SELECT cast_off FROM works WHERE work_key=?').get(k).cast_off, '["俳優乙"]');
    assert.doesNotMatch(await recommend(env, a), /出演 <b>俳優乙<\/b>/);
    assert.match((await step(env, a, {get: '/api/screen/works'})).body.body_html, /いま 1 人を「観た回に出ていなかった」にしています/);
    // Back to everyone.
    assert.equal((await step(env, a, {post: '/api/cast_seen', body: {work_key: k, off: []}})).status, 200);
    assert.match(await recommend(env, a), /出演 <a class="rsl"[^>]*><b>俳優乙<\/b><\/a>/);
    await step(env, a, {post: '/api/cast_seen', body: {work_key: k, off: ['俳優乙']}});
    await step(env, a, {post: '/api/link_stage', body: {work_key: k, stage_id: '103'}});
    assert.equal(sqlite.prepare('SELECT cast_off FROM works WHERE work_key=?').get(k).cast_off, '');
  } finally { sqlite.close(); }
});
