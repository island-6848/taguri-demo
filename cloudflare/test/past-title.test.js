// 過去の公演を題名の途中の語でも引く（起案者の指示 2026-10-24「検索しても今年の3月とかの公演が候補に出てこないのはなぜ？」→「OK」）。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {gramShard, bigrams, titleKey, TITLE_IDX} from '../src/stage-search.js';
import {setup, step, signIn} from './screens/harness.js';

test('the shard of a pair is the same as deliver_past_index.shard_of', () => {
  assert.deepEqual([gramShard('果て'), gramShard('白酒')], [0xd7, 0x18]);   // test_deliver_past_index.py と同じ値
});

/** R2 の題名の索引を、渡した公演から deliver_past_index.title_shards と同じ形で作る */
function fakeIndex(stages) {
  const files = new Map(), gets = [];
  for (const [sid, title] of [...stages].sort((a, b) => Number(b[0]) - Number(a[0]))) {
    for (const g of bigrams(titleKey(title))) {
      const key = `${TITLE_IDX}${gramShard(g).toString(16).padStart(2, '0')}.json`;
      const f = files.get(key) || {v: 1, grams: {}};
      (f.grams[g] ||= []).includes(sid) || f.grams[g].push(sid);
      files.set(key, f);
    }
  }
  return {gets, get: async key => { gets.push(key); return files.has(key) ? {json: async () => files.get(key)} : null; }};
}

function addPast(sqlite, rows) {
  const ins = sqlite.prepare("INSERT INTO past_stage(stage_id,title,tkey,start,end,venue,grp,pref,people) VALUES(?,?,?,?,?,'夢空間','',?,'[]')");
  for (const [sid, title, start] of rows) ins.run(sid, title, titleKey(title), start, start, '東京都');
}

const PAST = [['400101', '桃月庵白酒 独演会 白酒むふふ vol.32', '2026-03-23'], ['400102', '白酒を飲む夜', '2026-02-01'], ['400103', '別の芝居', '2026-03-01']];

test('登録の候補: a word in the middle of a past title is found through the index', async () => {
  const {env, sqlite} = setup();
  const a = await signIn(env);
  try {
    addPast(sqlite, PAST);
    // 索引が無い（まだ届いていない）ときは、これまでどおり先頭一致だけ
    const before = (await step(env, a, {get: '/api/suggest?q=' + encodeURIComponent('独演会')})).body.rows;
    assert.deepEqual(before.filter(r => r.kind === 'stage').map(r => r.stage_id), []);
    env.POSTERS = fakeIndex(PAST);
    const rows = (await step(env, a, {get: '/api/suggest?q=' + encodeURIComponent('独演会')})).body.rows;
    assert.deepEqual(rows.filter(r => r.kind === 'stage').map(r => r.stage_id), ['400101']);
    // 先頭一致の公演が先、途中に含む公演が後
    const both = (await step(env, a, {get: '/api/suggest?q=' + encodeURIComponent('白酒')})).body.rows.filter(r => r.kind === 'stage');
    assert.deepEqual(both.map(r => r.stage_id), ['400102', '400101']);
    assert.ok(env.POSTERS.gets.every(k => k.startsWith(TITLE_IDX)));
  } finally { sqlite.close(); }
});

test('探す: a past title is found by a word in its middle', async () => {
  const {env, sqlite} = setup();
  const a = await signIn(env);
  try {
    addPast(sqlite, PAST);
    env.POSTERS = fakeIndex(PAST);
    const html = (await step(env, a, {get: '/api/screen/search?q=' + encodeURIComponent('むふふ')})).body.body_html;
    assert.match(html, /桃月庵白酒 独演会 白酒むふふ vol\.32/);
    assert.doesNotMatch(html, /別の芝居/);
  } finally { sqlite.close(); }
});
