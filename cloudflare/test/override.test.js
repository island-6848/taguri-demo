// 管理者が手で直した公演の情報（migration 0028 stage_override、tools/admin）を画面に重ねる。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {applySynopsis, mergeInfo, priceRange} from '../src/screens/override.js';
import {setup, step, signIn} from './screens/harness.js';

const here = p => new URL(p, import.meta.url).pathname;
const FIXTURE = JSON.parse(execFileSync('python3', [here('./screens/recommend_fixture.py')], {encoding: 'utf8', maxBuffer: 64 * 1024 * 1024}));

test('the あらすじ block is replaced; themes alone keep the card text; a card without the block gets one', () => {
  const card = '<article class="ticket recommend"><h3>x</h3><div class="syn" data-stage="7"><p class="txt">元の文 &amp; 続き</p><div class="tags"><span class="tag">#旅</span></div><span class="src">［出典］</span><details class="handt"><div>form</div></details></div><div class="after">a</div></article>';
  const both = applySynopsis(card, '7', {synopsis: '手で入れた<文>', themes: ['家族', '海'], info: {}});
  assert.match(both, /<div class="syn" data-stage="7"><p class="txt">手で入れた&lt;文&gt;<\/p><div class="tags"><span class="tag">#家族<\/span><span class="tag">#海<\/span><\/div><span class="src">［たぐりの管理者が入れた内容です］<\/span>/);
  assert.doesNotMatch(both, /元の文|handt/);
  assert.match(both, /<div class="after">a<\/div><\/article>$/);
  const tagsOnly = applySynopsis(card, '7', {synopsis: null, themes: ['家族'], info: {}});
  assert.match(tagsOnly, /<p class="txt">元の文 &amp; 続き<\/p><div class="tags"><span class="tag">#家族<\/span><\/div>/);
  assert.equal(applySynopsis(card, '7', {synopsis: null, themes: null, info: {}}), card);
  const bare = applySynopsis('<article class="ticket recommend"><h3>x</h3></article>', '8', {synopsis: '新しい文', themes: null, info: {}});
  assert.match(bare, /<h3>x<\/h3><div class="syn" data-stage="8"><p class="txt">新しい文<\/p>[\s\S]*<\/div><\/article>$/);
});

test('details laid over the entry: fields merged, venue/period replaced, others kept', () => {
  const s = {stage_id: '7', venue: '劇場A', pref: '東京都', period: 'a', url: 'https://x', fields: {'料金': '5,000円', '劇場': '劇場A'}, synopsis: ''};
  const got = mergeInfo(s, {synopsis: null, themes: null, info: {venue: '劇場B', fields: {'料金': '6,000円', 'タイムテーブル': '11月1日 19:00'}}});
  assert.deepEqual(got, {stage_id: '7', venue: '劇場B', pref: '東京都', period: 'a', url: 'https://x', fields: {'料金': '6,000円', '劇場': '劇場A', 'タイムテーブル': '11月1日 19:00'}, synopsis: ''});
});

test('a hand-entered synopsis shows on the recommend card for every user', async () => {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  const a = await signIn(env);
  try {
    for (const [title, date, sid, verdict] of [['終わった舞台', '2026-08-05', '103', '◎'], ['一日だけの舞台', '2026-09-05', '104', '×']]) {
      const key = (await step(env, a, {post: '/api/add_work', body: {title, date}})).body.work_key;
      await step(env, a, {post: '/api/link_stage', body: {work_key: key, stage_id: sid}});
      await step(env, a, {post: '/api/rate', body: {work_key: key, verdict}});
    }
    sqlite.prepare("INSERT INTO stage_override(stage_id,synopsis,themes,info,updated_at) VALUES('101',?,?,?,?)")
      .run('管理者が入れたあらすじ', JSON.stringify(['港町']), JSON.stringify({fields: {'料金（1枚あたり）': '全席指定：4,500円'}}), '2026-10-17T00:00:00Z');
    const html = (await step(env, a, {get: '/api/screen/recommend'})).body.body_html;
    assert.match(html, /<div class="syn" data-stage="101"><p class="txt">管理者が入れたあらすじ<\/p><div class="tags"><span class="tag">#港町<\/span><\/div>/);
    assert.match(html, /<span class="price">全席指定：4,500円<\/span>/);
    assert.match(html, /<article class="ticket recommend" data-yen="4500-4500"/);
  } finally { sqlite.close(); }
});

test('priceRange matches render_recommend.price_range', () => {
  assert.deepEqual(priceRange('一般 5,000円 学生 3,000円【発売日】2026/09/01'), [3000, 5000]);
  assert.deepEqual(priceRange('入場無料'), [0, 0]);
  assert.deepEqual(priceRange('未定'), null);
  // 公演ページの欄の形（幅の行・発売日の行・券種の行）。発売日の行より後ろの金額も読む（2026-10-18）
  assert.deepEqual(priceRange('12,000円 ～ 12,000円\n【発売日】2026/09/01\nS席：12,000円\nU-25：6,000円'), [6000, 12000]);
});

// 起案者の質問 2026-10-17「すでにあらすじが取れている公演なのに、各画面に実際の文章が表示されていないのはなぜ？」
// カードは古い版のまま（あらすじ無し）でも、公演一覧に読み取り済みのあらすじが届いていれば、画面ではそれを出す
test('a card built before the synopsis was read shows the one the catalogue already has', async () => {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  const a = await signIn(env);
  try {
    for (const [title, date, sid, verdict] of [['終わった舞台', '2026-08-05', '103', '◎'], ['一日だけの舞台', '2026-09-05', '104', '×']]) {
      const key = (await step(env, a, {post: '/api/add_work', body: {title, date}})).body.work_key;
      await step(env, a, {post: '/api/link_stage', body: {work_key: key, stage_id: sid}});
      await step(env, a, {post: '/api/rate', body: {work_key: key, verdict}});
    }
    assert.match((await step(env, a, {get: '/api/screen/recommend'})).body.body_html, /<div class="syn no" data-stage="101">/);
    sqlite.prepare("INSERT INTO catalogue(id,title,date,metadata) VALUES('101','x','2026-11-01',?) ON CONFLICT(id) DO UPDATE SET metadata=excluded.metadata")
      .run(JSON.stringify({synopsis: '港町に<帰ってきた>男の話。'}));
    const html = (await step(env, a, {get: '/api/screen/recommend'})).body.body_html;
    assert.match(html, /<div class="syn" data-stage="101"><p class="txt">港町に&lt;帰ってきた&gt;男の話。<\/p><span class="src">［出典: 公演の紹介文］<\/span><button class="mrb" data-more="1">続きを読む<\/button><details class="handt">/);
    assert.doesNotMatch(html, /あらすじを取れませんでした/);
    // 手で入れたあらすじがあれば、そちらが勝つ
    sqlite.prepare("INSERT INTO stage_override(stage_id,synopsis,themes,info,updated_at) VALUES('101','管理者の文',NULL,'{}','x')").run();
    assert.match((await step(env, a, {get: '/api/screen/recommend'})).body.body_html, /<p class="txt">管理者の文<\/p>/);
  } finally { sqlite.close(); }
});
