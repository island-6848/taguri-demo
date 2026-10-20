// 作品ごとに分ける画面と API（/api/pieces、dec-split-pieces）: 記録は 1 件のまま、作品ごとに作品名・評価・感想・
// その作品に出ていた出演者を持ち、推薦は作品ごとの評価を使う。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {setup, step, signIn} from './screens/harness.js';

const here = p => new URL(p, import.meta.url).pathname;
const FIXTURE = JSON.parse(execFileSync('python3', [here('./screens/recommend_fixture.py')], {encoding: 'utf8', maxBuffer: 64 * 1024 * 1024}));
function withIndex() {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  // 102（俳優乙）をこれからの公演にする
  sqlite.exec("UPDATE rec_stage SET start='2026-12-01', end='2026-12-10' WHERE stage_id='102'");
  return {env, sqlite};
}
async function rateSeen(env, u, title, date, sid, verdict) {
  const key = (await step(env, u, {post: '/api/add_work', body: {title, date}})).body.work_key;
  assert.equal((await step(env, u, {post: '/api/link_stage', body: {work_key: key, stage_id: sid}})).status, 200);
  assert.equal((await step(env, u, {post: '/api/rate', body: {work_key: key, verdict}})).status, 200);
  return key;
}
const recommend = async (env, u) => (await step(env, u, {get: '/api/screen/recommend'})).body.body_html;
const pieces = (env, u, body) => step(env, u, {post: '/api/pieces', body});
const OTSU = /data-stage="102"[\s\S]*?出演 <a class="rsl"[^>]*><b>俳優乙<\/b><\/a>/;

test('a record is split into pieces on request, and kept as one record', async () => {
  const {env, sqlite} = withIndex();
  const a = await signIn(env), b = await signIn(env);
  try {
    const k = await rateSeen(env, a, '舞台ひとつめ', '2026-08-01', '101', '◎');
    // The editor offers it, unsplit by default.
    assert.match((await step(env, a, {get: '/api/screen/works'})).body.body_html, /data-pieces-open="[^"]+">作品ごとに評価・感想を付ける/);
    const got = await pieces(env, a, {work_key: k});
    assert.equal(got.status, 200);
    assert.deepEqual([got.body.cast, got.body.pieces, got.body.grades.map(g => g[0])], [['俳優乙', '俳優甲'], [], ['◎', '○', '△', '×']]);
    // One piece, a name not in the cast, a duplicate title, an unknown grade, someone else's record: refused.
    assert.equal((await pieces(env, a, {work_key: k, pieces: [{title: 'ひとつ'}]})).status, 400);
    assert.equal((await pieces(env, a, {work_key: k, pieces: [{title: 'A', cast: ['だれか']}, {title: 'B'}]})).status, 400);
    assert.equal((await pieces(env, a, {work_key: k, pieces: [{title: 'A'}, {title: 'A'}]})).status, 400);
    assert.equal((await pieces(env, a, {work_key: k, pieces: [{title: 'A', verdict: '◎◎'}, {title: 'B'}]})).status, 400);
    assert.equal((await pieces(env, b, {work_key: k})).status, 400);
    // Saved: the cast of each piece, everyone stored as ''.
    const saved = await pieces(env, a, {work_key: k, pieces: [
      {title: 'かもめ', verdict: '×', note: '長かった', cast: ['俳優乙']},
      {title: '熊', verdict: '◎', cast: ['俳優乙', '俳優甲']}]});
    assert.deepEqual([saved.status, saved.body.n], [200, 2]);
    assert.deepEqual(sqlite.prepare('SELECT idx, title, verdict, note, cast_in FROM work_piece WHERE work_key=? ORDER BY idx').all(k).map(r => ({...r})),
      [{idx: 0, title: 'かもめ', verdict: '×', note: '長かった', cast_in: '["俳優乙"]'}, {idx: 1, title: '熊', verdict: '◎', note: '', cast_in: ''}]);
    // Still one record; its row lists the pieces with their grades.
    assert.equal(sqlite.prepare('SELECT count(*) AS n FROM works WHERE user_id=(SELECT user_id FROM works WHERE work_key=?)').get(k).n, 1);
    const html = (await step(env, a, {get: '/api/screen/works'})).body.body_html;
    assert.match(html, /作品ごと（2 作品）<\/span><ol><li><span class="pct">かもめ<\/span><span class="pcv" data-mark="×">×<\/span><span class="pcn">長かった<\/span><\/li><li><span class="pct">熊<\/span>/);
    assert.match(html, /作品ごとの評価・感想を直す（2 作品）/);
    // Back to unsplit; the record stays.
    assert.equal((await pieces(env, a, {work_key: k, pieces: []})).status, 200);
    assert.equal(sqlite.prepare('SELECT count(*) AS n FROM work_piece').get().n, 0);
    assert.equal(sqlite.prepare('SELECT count(*) AS n FROM works WHERE work_key=?').get(k).n, 1);
  } finally { sqlite.close(); }
});

test('the recommendations follow each piece\'s rating and cast', async () => {
  const {env, sqlite} = withIndex();
  const a = await signIn(env);
  try {
    // 101 (俳優乙・俳優甲) ◎ raises the coming 102 through 俳優乙.
    const k = await rateSeen(env, a, '舞台ひとつめ', '2026-08-01', '101', '◎');
    await rateSeen(env, a, '一日だけの舞台', '2026-09-05', '104', '×');
    assert.match(await recommend(env, a), OTSU);
    // Split: 俳優乙 was only in the piece rated ×, so 102 no longer rises through 俳優乙.
    await pieces(env, a, {work_key: k, pieces: [{title: 'かもめ', verdict: '×', cast: ['俳優乙']}, {title: '熊', verdict: '◎', cast: ['俳優甲']}]});
    assert.doesNotMatch(await recommend(env, a), OTSU);
    // Pieces left unrated fall back to the record's own rating.
    await pieces(env, a, {work_key: k, pieces: [{title: 'かもめ', cast: ['俳優乙']}, {title: '熊', cast: ['俳優甲']}]});
    assert.match(await recommend(env, a), OTSU);
  } finally { sqlite.close(); }
});

test('renaming, relinking and deleting the record carry its pieces along', async () => {
  const {env, sqlite} = withIndex();
  const a = await signIn(env);
  try {
    const k = await rateSeen(env, a, '舞台ひとつめ', '2026-08-01', '101', '◎');
    await pieces(env, a, {work_key: k, pieces: [{title: 'かもめ', cast: ['俳優乙']}, {title: '熊'}]});
    // A new title moves the pieces to the new key.
    const fixed = await step(env, a, {post: '/api/fix_work', body: {work_key: k, title: '舞台ひとつめ（短編集）'}});
    assert.equal(fixed.status, 200);
    const k2 = fixed.body.work_key;
    assert.notEqual(k2, k);
    assert.deepEqual(sqlite.prepare('SELECT DISTINCT work_key FROM work_piece').all().map(r => r.work_key), [k2]);
    // Linking another stage resets who was in each piece (the names were the old stage's).
    assert.equal((await step(env, a, {post: '/api/link_stage', body: {work_key: k2, stage_id: '103'}})).status, 200);
    assert.deepEqual(sqlite.prepare('SELECT cast_in FROM work_piece ORDER BY idx').all().map(r => r.cast_in), ['', '']);
    // Deleting the record (取り消して、完全に取り消す) deletes its pieces.
    assert.equal((await step(env, a, {post: '/api/drop_work', body: {work_key: k2}})).status, 200);
    assert.equal(sqlite.prepare('SELECT count(*) AS n FROM work_piece').get().n, 2);
    assert.equal((await step(env, a, {post: '/api/purge_work', body: {key: k2}})).status, 200);
    assert.equal(sqlite.prepare('SELECT count(*) AS n FROM work_piece').get().n, 0);
  } finally { sqlite.close(); }
});
