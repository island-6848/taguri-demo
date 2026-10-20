// あらすじのハッシュタグ（題材の語）の公演の一覧（screens/tagged.js）。起案者の指示 2026-10-18
// 「あらすじのハッシュタグ押したらそれがついてる公演一覧が出るようにして」
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {setup, step, signIn} from './screens/harness.js';
import {tagWord, byProduction, TAG_SHOW} from '../src/screens/tagged.js';

const here = p => new URL(p, import.meta.url).pathname;
const FIXTURE = JSON.parse(execFileSync('python3', [here('./screens/recommend_fixture.py')], {encoding: 'utf8', maxBuffer: 64 * 1024 * 1024}));
const screen = async (env, u, q) => (await step(env, u, {get: `/api/screen/tagged${q}`})).body;

/** The fixture's cards, with subject words: 101 家族・再生, 102 家族 (and 107, a second venue of 102 without words), 106 喜劇. */
function withWords() {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  sqlite.exec(`UPDATE rec_card SET ws='家族\n再生' WHERE stage_id='101'`);
  sqlite.exec(`UPDATE rec_card SET ws='家族' WHERE stage_id='102'`);
  sqlite.exec(`UPDATE rec_card SET ws='喜劇' WHERE stage_id='106'`);
  sqlite.exec(`INSERT INTO rec_card(ver,stage_id,html,title,tour,start,end,pref,gnz,blob,ws,synz)
    SELECT ver,'107',replace(html,'data-stage="102"','data-stage="107"'),title,tour,'2026-10-24','2026-10-26','愛知県',gnz,blob,'',synz FROM rec_card WHERE stage_id='102'`);
  sqlite.exec(`INSERT INTO rec_stage(ver,stage_id,title,tkey,grp,tour,gkey,start,end,credits,entry)
    SELECT ver,'107',title,tkey,grp,tour,gkey,'2026-10-24','2026-10-26',credits,json_set(entry,'$.theater','劇場E','$.pref','愛知県') FROM rec_stage WHERE stage_id='102'`);
  // 読んだ文の数を数える（rec_card をなめる問い合わせは 1 回だけのはず）
  const sqls = [];
  const prepare = env.DB.prepare;
  env.DB.prepare = sql => { sqls.push(sql); return prepare(sql); };
  return {env, sqlite, sqls};
}

test('tagWord drops the leading # and keeps at most 30 characters', () => {
  assert.equal(tagWord('#家族'), '家族');
  assert.equal(tagWord('＃ 再生 '), '再生');
  assert.equal(Array.from(tagWord('あ'.repeat(40))).length, 30);
  assert.equal(tagWord(''), '');
});

test('byProduction: one row per tour, the earliest venue with the word shown, every venue kept for the schedule', () => {
  const rows = byProduction([
    {stage_id: '2', tour: 't', start: '2026-11-05', hit: true}, {stage_id: '3', tour: 't', start: '2026-10-01', hit: false},
    {stage_id: '1', tour: '', start: '2026-10-20', hit: true}, {stage_id: '4', tour: 'u', start: '2026-10-01', hit: false}]);
  assert.deepEqual(rows.map(r => [r.stage_id, r.sids]), [['1', ['1']], ['2', ['3', '2']]]);
});

test('the stages whose subject words include the word, as cards; a whole word only; the tour in one card', async () => {
  const {env, sqlite, sqls} = withWords();
  const a = await signIn(env);
  try {
    sqls.length = 0;
    const html = (await screen(env, a, '?w=%E5%AE%B6%E6%97%8F')).body_html;   // 家族
    assert.match(html, /<h1><span class="ftag big">#家族<\/span> の公演<\/h1>/);
    assert.match(html, /<p class="rcount">全 2 件<\/p>/);
    // 上演日の近い順（102 は 10/1 から、101 は 11/1 から）。ツアーの 2 つめの会場 107 は 102 のカードの日程に入る
    const order = [...html.matchAll(/<article class="ticket (\w+)" data-stage="(\d+)"/g)].map(m => m[2]);
    assert.deepEqual(order, ['102', '101']);
    assert.match(html, /<div class="whyh top">[\s\S]*?ヒットした箇所：<\/div><ul class="why top"><li class="rs found"><span class="net">題材<\/span>#家族<\/li><\/ul>/);
    const c102 = html.slice(html.indexOf('data-stage="102"'), html.indexOf('data-stage="101"'));
    assert.match(c102, /<div class="tourfull v2">/);   // 会場が 2 つ（one ではない）
    assert.equal((c102.match(/class="tf-row/g) || []).length, 2);
    // 興味あり・興味なし・購入済を押せる
    assert.match(html, /<span class="btns" data-stage="101"><button data-v="interest">/);
    // 語の一部では当たらない（「家」）。当たらないときの文
    assert.match((await screen(env, a, '?w=%E5%AE%B6')).body_html, /いま、題材に「家」が付いている、今後の公演はありません。/);
    // rec_card をなめるのは 1 回（あとはカードの分だけ stage_id で引く）
    sqls.length = 0;
    await screen(env, a, '?w=%E5%86%8D%E7%94%9F');   // 再生
    const scans = sqls.filter(s => /FROM rec_card/.test(s) && !/stage_id IN/.test(s));
    assert.equal(scans.length, 1, scans.join('\n'));
  } finally { sqlite.close(); }
});

test('hand-entered subject words (stage_override) decide for their stage, as the card shows them', async () => {
  const {env, sqlite} = withWords();
  const a = await signIn(env);
  try {
    // 102 の題材を手で「旅」だけにすると、102（とツアーの 107）は #家族 から外れ、#旅 に出る
    sqlite.exec(`INSERT INTO stage_override(stage_id,synopsis,themes,info,updated_at) VALUES('102',NULL,'["旅"]','{}','2026-10-12T00:00:00Z')`);
    const fam = (await screen(env, a, '?w=%E5%AE%B6%E6%97%8F')).body_html;
    assert.deepEqual([...fam.matchAll(/<article class="ticket \w+" data-stage="(\d+)"/g)].map(m => m[1]), ['101']);
    const trip = (await screen(env, a, '?w=%23%E6%97%85')).body_html;   // #旅
    assert.match(trip, /<h1><span class="ftag big">#旅<\/span> の公演<\/h1>/);
    assert.deepEqual([...trip.matchAll(/<article class="ticket \w+" data-stage="(\d+)"/g)].map(m => m[1]), ['102']);
  } finally { sqlite.close(); }
});

test('an answered stage says so; 興味あり is drawn as an interest card', async () => {
  const {env, sqlite} = withWords();
  const a = await signIn(env);
  try {
    assert.equal((await step(env, a, {post: '/api/react', body: {stage_id: '101', value: 'interest', nofill: true}})).status, 200);
    const html = (await screen(env, a, '?w=%E5%AE%B6%E6%97%8F')).body_html;
    assert.match(html, /<article class="ticket interest" data-stage="101"/);
    assert.match(html, /<li class="rs state">追いかけています（興味ありと答えました）<\/li>/);
  } finally { sqlite.close(); }
});

test('no word: a short explanation; many stages: pages of TAG_SHOW', async () => {
  const {env, sqlite} = withWords();
  const a = await signIn(env);
  try {
    assert.match((await screen(env, a, '')).body_html, /題材の語がありません/);
    const n = TAG_SHOW + 3;
    for (let i = 0; i < n; i++) {
      sqlite.exec(`INSERT INTO rec_card(ver,stage_id,html,title,tour,start,end,pref,gnz,blob,ws,synz)
        SELECT ver,'${900 + i}',replace(html,'data-stage="101"','data-stage="${900 + i}"'),title,'','2026-12-${String(10 + (i % 15)).padStart(2, '0')}','2026-12-31','',gnz,blob,'群像',synz FROM rec_card WHERE stage_id='101'`);
    }
    const p1 = (await screen(env, a, '?w=%E7%BE%A4%E5%83%8F')).body_html;   // 群像
    assert.match(p1, new RegExp(`全 ${n} 件中 1〜${TAG_SHOW} 件目を表示中`));
    assert.equal((p1.match(/<article class="ticket/g) || []).length, TAG_SHOW);
    assert.match(p1, /<a class="mpage" href="\/recommend\/tag\?t=__TAGURI_TOKEN__&amp;w=%E7%BE%A4%E5%83%8F&amp;p=2">次の 3 件 →<\/a>/);
    const p2 = (await screen(env, a, '?w=%E7%BE%A4%E5%83%8F&p=2')).body_html;
    assert.equal((p2.match(/<article class="ticket/g) || []).length, 3);
  } finally { sqlite.close(); }
});
