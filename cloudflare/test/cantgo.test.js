// 4 択（起案者の指示 2026-10-17「興味あり、興味なし、購入済、行けないの 4 択にして」）。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {setup, step, signIn} from './screens/harness.js';
import {buttons, interestButtons} from '../src/screens/cards.js';
import {droppedKind} from '../src/recommend.js';

const here = p => new URL(p, import.meta.url).pathname;
const FIXTURE = JSON.parse(execFileSync('python3', [here('./screens/recommend_fixture.py')], {encoding: 'utf8', maxBuffer: 64 * 1024 * 1024}));

test('the answers: three on おすすめ, and 興味なし・購入済 on 興味あり (no 行けない since 2026-10-20)', () => {
  const vs = html => [...html.matchAll(/data-v="(\w+)">([^<]+)</g)].map(m => [m[1], m[2]]);
  assert.deepEqual(vs(buttons('1')), [['interest', '興味あり'], ['nointerest', '興味なし'], ['owned', '購入済']]);
  assert.deepEqual(vs(interestButtons('1')), [['nointerest', '興味なし'], ['owned', '購入済']]);
  assert.doesNotMatch(interestButtons('1'), /cantgo|行けない/);
  // A theatre is no kind of reason any more (起案者 2026-10-17「ただ会場で出てくるのは不要」).
  assert.ok(droppedKind('#会場', '本多劇場'));
});

test('行けない takes the stage off the recommendations, keeps it out of 興味あり, and says so on 開幕リマインド', async () => {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  const a = await signIn(env);
  try {
    for (const [title, date, sid, verdict] of [['終わった舞台', '2026-08-05', '103', '◎'], ['一日だけの舞台', '2026-09-05', '104', '×']]) {
      const key = (await step(env, a, {post: '/api/add_work', body: {title, date}})).body.work_key;
      await step(env, a, {post: '/api/link_stage', body: {work_key: key, stage_id: sid}});
      await step(env, a, {post: '/api/rate', body: {work_key: key, verdict}});
    }
    assert.match((await step(env, a, {get: '/api/screen/recommend'})).body.body_html, /data-stage="101"/);
    const r = await step(env, a, {post: '/api/react', body: {stage_id: '101', value: 'cantgo', nofill: true}});
    assert.equal(r.status, 200);
    assert.equal(sqlite.prepare("SELECT interest FROM reaction WHERE stage_id='101'").get().interest, 2);
    assert.doesNotMatch((await step(env, a, {get: '/api/screen/recommend'})).body.body_html, /data-stage="101"/);
    assert.doesNotMatch((await step(env, a, {get: '/api/screen/interest'})).body.body_html, /data-stage="101"/);
  } finally { sqlite.close(); }
});

test('the count line: 「県／N 件中 上位 M 件を表示中」, and the two removed sentences are gone', async () => {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  const a = await signIn(env);
  try {
    for (const [title, date, sid, verdict] of [['終わった舞台', '2026-08-05', '103', '◎'], ['一日だけの舞台', '2026-09-05', '104', '×']]) {
      const key = (await step(env, a, {post: '/api/add_work', body: {title, date}})).body.work_key;
      await step(env, a, {post: '/api/link_stage', body: {work_key: key, stage_id: sid}});
      await step(env, a, {post: '/api/rate', body: {work_key: key, verdict}});
    }
    const all = (await step(env, a, {get: '/api/screen/recommend'})).body.body_html;
    assert.match(all, /<p class="rcount"><b>全国<\/b>／\d+ 件中 上位 \d+ 件を表示中<\/p>/);
    assert.doesNotMatch(all, /現在のあなたの評価|気になる公演がおすすめに無いときは/);
    const pref = sqlite.prepare("SELECT entry FROM rec_stage WHERE stage_id='101'").get();
    const p = JSON.parse(pref.entry).pref;
    if (p) assert.match((await step(env, a, {get: '/api/screen/recommend?f=1&pref=' + encodeURIComponent(p)})).body.body_html,
      new RegExp(`<p class="rcount"><b>${p}</b>／\\d+ 件中 上位 \\d+ 件を表示中</p>`));
  } finally { sqlite.close(); }
});

test('興味あり cards get the same schedule block as おすすめ (venue rows, calendar)', async () => {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  const e = JSON.parse(sqlite.prepare("SELECT entry FROM rec_stage WHERE stage_id='101'").get().entry);
  e.fields = {...e.fields, 'タイムテーブル': '11月1日(日) 13:00\n11月3日(火) 19:00'};
  sqlite.prepare("UPDATE rec_stage SET entry=? WHERE stage_id='101'").run(JSON.stringify(e));
  const a = await signIn(env);
  try {
    assert.equal((await step(env, a, {post: '/api/react', body: {stage_id: '101', value: 'interest', nofill: true}})).status, 200);
    const html = (await step(env, a, {get: '/api/screen/interest'})).body.body_html;
    assert.match(html, /<article class="ticket interest" data-stage="101"[\s\S]*<div class="tourfull v2 one"><details class="tf-row" open><summary class="tf-head"><span class="tf-when">11\/1〜11\/10<span class="tf-cnt">（2 回）<\/span><\/span><\/summary>/);   // 「詳細」の字は無し（起案者の指示 2026-10-18）
    assert.match(html, /<span class="tf-cnt">（2 回）<\/span>[\s\S]*?<div class="tf-body"><table class="ttb"/);
  } finally { sqlite.close(); }
});

test('お気に入り cards use the same schedule block, with no 「このおすすめの日程」', async () => {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  const a = await signIn(env);
  try {
    assert.equal((await step(env, a, {post: '/api/favourite', body: {action: 'add', kind: '人', name: '俳優甲'}})).status, 200);
    const html = (await step(env, a, {get: '/api/screen/favourites'})).body.body_html;
    assert.match(html, /<article class="ticket favourite"[\s\S]*<div class="tourfull v2/);
    assert.doesNotMatch(html, /このおすすめの日程/);
  } finally { sqlite.close(); }
});

// 行けばよかった（起案者の指示 2026-10-20「興味ありにしたけど購入済みにならなかったら自動的に行けばよかった扱いにすれば良い」）
test('興味あり on a stage that ended without 購入済 is listed under 行けばよかった; 購入済 or a record of it keeps it out', async () => {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  const a = await signIn(env), b = await signIn(env);
  const reg = async c => (await step(env, c, {get: '/api/screen/register'})).body.body_html;
  try {
    const ended = sqlite.prepare("SELECT stage_id, title FROM rec_stage WHERE end<>'' AND end<'2026-10-01' LIMIT 1").get();
    assert.ok(ended, 'the fixture has an ended stage');
    assert.equal((await step(env, a, {post: '/api/react', body: {stage_id: ended.stage_id, value: 'interest', nofill: true}})).status, 200);
    const html = await reg(a);
    assert.match(html, new RegExp(`<b class="mt">${ended.title}</b>[^]*?興味ありのまま終わった`));
    assert.match(html, /<span class="badge part">1 件<\/span>/);
    assert.doesNotMatch(await reg(b), new RegExp(ended.title));          // other users see nothing
    // 購入済にしていれば入らない
    assert.equal((await step(env, b, {post: '/api/react', body: {stage_id: ended.stage_id, value: 'owned', nofill: true}})).status, 200);
    assert.doesNotMatch(await reg(b), /興味ありのまま終わった/);
    // 観た記録にあれば入らない
    const key = (await step(env, a, {post: '/api/add_work', body: {title: ended.title, date: '2026-08-05'}})).body.work_key;
    await step(env, a, {post: '/api/link_stage', body: {work_key: key, stage_id: ended.stage_id}});
    assert.doesNotMatch(await reg(a), /興味ありのまま終わった/);
  } finally { sqlite.close(); }
});
