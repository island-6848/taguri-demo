// ツアー公演を何回も足したとき・まとめた記録を見たとき（起案者の問い 2026-10-21「ツアー公演を複数回追加するとき、またまとめた公演を見るとき
// 周辺のUXが悪い」、ux-tour-repeat-merge-1021）。まとめた回の日付・劇場・開演を捨てず、回数・劇場を回ごとに数え、1 回ずつ分けられる
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {setup, step, signIn} from './screens/harness.js';

async function withTour(fn) {
  const {env, sqlite} = setup();
  const a = await signIn(env);
  const ins = sqlite.prepare("INSERT INTO past_stage(stage_id,title,tkey,start,end,venue,grp,pref,people) VALUES(?,'旅の芝居','旅の芝居',?,?,?,'劇団甲','東京都','[]')");
  ins.run('710001', '2025-07-01', '2025-07-10', '劇場A');
  ins.run('710002', '2025-08-01', '2025-08-03', '劇場B');
  ins.run('710003', '2025-08-20', '2025-08-24', '劇場E');
  try { await fn(env, a, sqlite); } finally { sqlite.close(); }
}
const add = async (env, a, body) => (await step(env, a, {post: '/api/add_work', body: {title: '旅の芝居', ...body}})).body;
const diary = async (env, a, g = '') => (await step(env, a, {get: `/api/screen/works${g ? '?g=' + g : ''}`})).body.body_html;
// 劇場A で 2 回、劇場B で昼と夜、劇場E で 1 回（劇場A を選んだまま 8/22 を足す）
async function fiveVisits(env, a) {
  await add(env, a, {stage_id: '710001', venue: '劇場A', date: '2025-07-05'});
  await add(env, a, {stage_id: '710001', venue: '劇場A', date: '2025-07-08'});
  await add(env, a, {stage_id: '710002', venue: '劇場B', date: '2025-08-02', time: '13:00'});
  await add(env, a, {stage_id: '710002', venue: '劇場B', date: '2025-08-02', time: '18:00'});
  return add(env, a, {stage_id: '710001', venue: '劇場A', date: '2025-08-22', repeat: true});
}

test('a record linked again to the theatre playing that day takes that theatre’s name', async () => withTour(async (env, a, sqlite) => {
  const r = await fiveVisits(env, a);
  assert.equal(r.stage_id, '710003');
  assert.equal(r.venue, '劇場E');
  assert.deepEqual({...sqlite.prepare("SELECT stage_id, venue FROM works WHERE first_date='2025-08-22'").get()}, {stage_id: '710003', venue: '劇場E'});
  // 劇場を手で別の名前にしていたら、そのまま
  const own = await add(env, a, {stage_id: '710001', venue: '劇場Eの小ホール', date: '2025-08-23'});
  assert.equal(own.venue, undefined);
  assert.equal(sqlite.prepare("SELECT venue FROM works WHERE first_date='2025-08-23'").get().venue, '劇場Eの小ホール');
}));

test('the merged record keeps every visit: count, theatres, and one row per visit', async () => withTour(async (env, a) => {
  await fiveVisits(env, a);
  const html = await diary(env, a);
  assert.match(html, /作品でまとめる<span class="mn">1<\/span>/);
  assert.match(html, /<div class="where"><span>劇場A ほか 2 会場<\/span> <span class="mtimes">5 回観た<\/span><\/div>/);
  const list = html.match(/<details class="visits"><summary>観た 5 回の日付と劇場<\/summary><ol>(.*?)<\/ol>/s)[1];
  assert.deepEqual([...list.matchAll(/<span class="vis-d">([^<]+)<\/span><span class="vis-v">([^<]+)<\/span>/g)].map(m => `${m[1]} ${m[2]}`),
    ['2025.07.05(土) 劇場A', '2025.07.08(火) 劇場A', '2025.08.02(土) 13:00 劇場B', '2025.08.02(土) 18:00 劇場B', '2025.08.22(金) 劇場E']);
  assert.equal([...list.matchAll(/data-unmerge-one=/g)].length, 4);   // 残した回（7/5）のほかに「分ける」
  // すべて表示: 回ごとに 1 行。直す欄は残した回の行にだけ
  const visit = await diary(env, a, 'visit');
  assert.match(visit, /すべて表示<span class="mn">5<\/span>/);
  assert.equal([...visit.matchAll(/<article class="rec-row/g)].length, 5);
  assert.equal([...visit.matchAll(/<details class="editor"/g)].length, 1);
  // 開演の時刻は日付の後ろ（2026.10.13(水) 13:00 の形。起案者の指示 2026-10-24）
  assert.match(visit, /<span class="ymd">2025\.08\.02\(土\) <span class="at">18:00<\/span><\/span>/);
}));

test('the account counts each visit at its own theatre', async () => withTour(async (env, a) => {
  await fiveVisits(env, a);
  await diary(env, a);
  const page = (await step(env, a, {get: '/api/screen/account'})).body.body_html;
  assert.match(page, /<b>1<\/b><span>観た作品/);
  assert.match(page, /<b>5<\/b><span>観た回数/);
  const rows = cls => [...page.match(new RegExp(`<ol class="rk ${cls}">(.*?)</ol>`, 's'))[1]
    .matchAll(/aria-label="(\d+) 位">\d+<\/b><span class="rk-name">(.*?)<\/span><span class="rk-bar".*?<small>([^<]+)<\/small>/g)]
    .map(m => `${m[1]}:${m[2].replace(/<[^>]+>/g, '')}:${m[3]}`);
  assert.deepEqual(rows('rk-visits'), ['1:劇場A、劇場B:2 回']);   // 劇場E は 1 回なので出さない
}));

test('one visit can be split off, and it keeps the rating', async () => withTour(async (env, a, sqlite) => {
  await fiveVisits(env, a);
  await diary(env, a);
  const kept = sqlite.prepare("SELECT work_key FROM works WHERE first_date='2025-07-05'").get().work_key;
  const e = sqlite.prepare("SELECT work_key FROM works WHERE first_date='2025-08-22'").get().work_key;
  await step(env, a, {post: '/api/rate', body: {work_key: kept, verdict: '4/5'}});
  const r = await step(env, a, {post: '/api/merge_work', body: {work_key: kept, unmerge: true, one: e}});
  assert.deepEqual([r.body.ok, r.body.n], [true, 1]);
  assert.equal(sqlite.prepare('SELECT count(*) AS n FROM merges').get().n, 3);
  assert.equal(sqlite.prepare('SELECT verdict FROM works WHERE work_key=?').get(e).verdict, '4/5');
  // 分けた回は、日記帳を開いてもまとめ直さない
  const html = await diary(env, a);
  assert.match(html, /作品でまとめる<span class="mn">2<\/span>/);
  assert.match(html, /観た 4 回の日付と劇場/);
  // まとまっていない回は分けられない
  assert.equal((await step(env, a, {post: '/api/merge_work', body: {work_key: kept, unmerge: true, one: e}})).status, 400);
}));

test('探す keeps a recorded tour on the list, marked with how many times it was recorded', async () => withTour(async (env, a) => {
  await fiveVisits(env, a);
  await diary(env, a);
  const html = (await step(env, a, {get: '/api/screen/search?q=' + encodeURIComponent('旅の芝居')})).body.body_html;
  assert.match(html, /<span class="badge part">記録あり 5 回<\/span>/);
  assert.match(html, /劇場A（2025\/7\/1〜2025\/7\/10）・記録あり 2 回<\/option>/);
  assert.match(html, /劇場E（2025\/8\/20〜2025\/8\/24）・記録あり 1 回<\/option>/);
}));
