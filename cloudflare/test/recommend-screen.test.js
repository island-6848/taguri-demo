// 今週のおすすめ on the Worker (screens/recommend.js): the ranking from the user's own
// works, the cards rendered by the Python batch (build_cards.py) with the rank, the
// reasons and the poster filled in, the prefecture filter, and the three-choice writes.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {setup, step, signIn} from './screens/harness.js';

const here = p => new URL(p, import.meta.url).pathname;
const FIXTURE = JSON.parse(execFileSync('python3', [here('./screens/recommend_fixture.py')], {encoding: 'utf8', maxBuffer: 64 * 1024 * 1024}));

async function withIndex() {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  return {env, sqlite};
}
async function rateSeen(env, cookie, title, date, sid, verdict) {
  const key = (await step(env, cookie, {post: '/api/add_work', body: {title, date}})).body.work_key;
  assert.equal((await step(env, cookie, {post: '/api/link_stage', body: {work_key: key, stage_id: sid}})).status, 200);
  assert.equal((await step(env, cookie, {post: '/api/rate', body: {work_key: key, verdict}})).status, 200);
  return key;
}

test('a new account gets no recommendations and is told what to do', async () => {
  const {env, sqlite} = await withIndex();
  const a = await signIn(env);
  try {
    const got = await step(env, a, {get: '/api/screen/recommend'});
    assert.equal(got.status, 200);
    assert.equal(got.body.title, '今週のおすすめ');
    assert.equal(got.body.moving, undefined);
    assert.match(got.body.body_html, /<h1>今週のおすすめはありません<\/h1>/);
    assert.doesNotMatch(got.body.body_html, /<article/);
    // 推薦を出すためのワンポイント (起案者 2026-10-14): what to do, in plain words.
    assert.match(got.body.body_html, /<h2>おすすめを出すためのワンポイント<\/h2>/);
    assert.match(got.body.body_html, /観た公演を 2 本以上、評価してください/);
  } finally { sqlite.close(); }
});

test('a ◎ on a stage recommends the coming stage of the same people, with the Python card and the reasons', async () => {
  const {env, sqlite} = await withIndex();
  const a = await signIn(env), b = await signIn(env);
  try {
    await rateSeen(env, a, '終わった舞台', '2026-08-05', '103', '◎');
    await rateSeen(env, a, '一日だけの舞台', '2026-09-05', '104', '×');
    const html = (await step(env, a, {get: '/api/screen/recommend'})).body.body_html;
    assert.match(html, /<h1>今週のおすすめ 1 件<\/h1>/);
    assert.match(html, /<article class="ticket recommend" data-stage="101"/);
    assert.doesNotMatch(html, /おすすめを出すためのワンポイント/);
    assert.match(html, /<span class="sn">No\.01<\/span>/);
    assert.match(html, /<li class="rs b"><span class="net">人物<\/span>出演 <b>俳優甲<\/b><span class="n">（『終わった舞台』）<\/span>/);
    assert.doesNotMatch(html, /<!--(rank|why|poster)-->/);
    assert.match(html, /<button data-v="interest">興味あり<\/button>/);
    // The other user sees none of it.
    assert.doesNotMatch((await step(env, b, {get: '/api/screen/recommend'})).body.body_html, /<article/);
    // Prefecture filter: ?f=1 holds it for this page only (not saved), an empty ?f=1 is 全国.
    const osaka = (await step(env, a, {get: '/api/screen/recommend?f=1&pref=' + encodeURIComponent('大阪府')})).body.body_html;
    assert.match(osaka, /<h1>大阪府のおすすめはありません<\/h1>/);
    assert.match((await step(env, a, {get: '/api/screen/recommend'})).body.body_html, /いまは<b>全国<\/b>/);
    assert.equal(sqlite.prepare("SELECT count(*) AS n FROM app_setting WHERE key='recommend_prefs'").get().n, 0);
    const tokyo = (await step(env, a, {get: '/api/screen/recommend?f=1&pref=' + encodeURIComponent('東京都')})).body.body_html;
    assert.match(tokyo, /<h1>東京都のおすすめ 1 件<\/h1>/);
    assert.match((await step(env, a, {get: '/api/screen/recommend?f=1'})).body.body_html, /いまは<b>全国<\/b>/);
    // A poster in R2 goes into the card.
    sqlite.exec("INSERT INTO poster(stage_id,file) VALUES('101','101.webp')");
    sqlite.exec("UPDATE rec_cache SET stamp='x'");
    assert.match((await step(env, a, {get: '/api/screen/recommend'})).body.body_html, /<img class="poster" src="\/img\/101\.webp\?t=/);
  } finally { sqlite.close(); }
});

test('answering a card takes it out of the recommendations, for this user only', async () => {
  const {env, sqlite} = await withIndex();
  const a = await signIn(env), b = await signIn(env);
  try {
    for (const u of [a, b]) {
      await rateSeen(env, u, '終わった舞台', '2026-08-05', '103', '◎');
      await rateSeen(env, u, '一日だけの舞台', '2026-09-05', '104', '×');
    }
    const got = await step(env, a, {post: '/api/react', body: {stage_id: '101', value: 'interest', nofill: true, siblings: []}});
    assert.equal(got.status, 200);
    assert.deepEqual({ok: got.body.ok, value: got.body.value, fill: got.body.fill}, {ok: true, value: 'interest', fill: undefined});
    const fill = await step(env, a, {post: '/api/react', body: {stage_id: '101', fill_only: true, shown: ['101']}});
    assert.equal(fill.body.fill.html, '');
    assert.match(fill.body.fill.said, /入れ替える候補はもうありません/);
    // Every candidate answered: the thank-you block with its advice, not the new-user tips
    const doneHtml = (await step(env, a, {get: '/api/screen/recommend'})).body.body_html;
    assert.match(doneHtml, /<h1>今週のおすすめにはすべて答えました<\/h1>/);
    assert.match(doneHtml, /回答ありがとうございました[\s\S]*<b>過去の観劇記録を足す<\/b>：/);
    assert.doesNotMatch(doneHtml, /おすすめを出すためのワンポイント|<template id="rec-thanks-t">/);
    const bHtml = (await step(env, b, {get: '/api/screen/recommend'})).body.body_html;
    assert.match(bHtml, /data-stage="101"/);
    assert.match(bHtml, /<template id="rec-thanks-t"><section class="card thx"/);
    // A note alone is saved without answering; bad input is refused.
    assert.equal((await step(env, b, {post: '/api/react', body: {stage_id: '101', note: '俳優甲が観たい'}})).status, 200);
    assert.match((await step(env, b, {get: '/api/screen/recommend'})).body.body_html, /data-stage="101"/);
    assert.equal((await step(env, b, {post: '/api/react', body: {stage_id: '101', value: 'maybe'}})).status, 400);
    assert.equal((await step(env, b, {post: '/api/react', body: {stage_id: '../x', value: 'interest'}})).status, 400);
    const rows = sqlite.prepare("SELECT user_id, stage_id, interest, note FROM reaction ORDER BY user_id").all().map(r => ({...r}));
    assert.equal(rows.length, 2);
  } finally { sqlite.close(); }
});

// 2026-10-14「おすすめの画面を移して」: the 効かせ方 sliders (app.weight_form, /api/weight).
test('効かせ方: the sliders show the saved steps and the counts; "効かせない" takes a group out of the ranking and the reasons; bad input is refused', async () => {
  const {env, sqlite} = await withIndex();
  const a = await signIn(env), b = await signIn(env);
  try {
    await rateSeen(env, a, '終わった舞台', '2026-08-05', '103', '◎');
    await rateSeen(env, a, '一日だけの舞台', '2026-09-05', '104', '×');
    let html = (await step(env, a, {get: '/api/screen/recommend'})).body.body_html;
    assert.match(html, /<details class="pbox wbox" id="weights">/);
    assert.match(html, /いまは<b>ふつう<\/b>/);
    assert.match(html, /<div class="wrow" data-grp="cast"><span class="wl">出演者<\/span><span class="wn">おすすめの候補 1 件で一致<\/span>/);
    assert.match(html, /<h1>今週のおすすめ 1 件<\/h1>/);
    const saved = await step(env, a, {post: '/api/weight', body: {weights: {cast: 'off', theme: 'max'}}});
    assert.equal(saved.status, 200);
    assert.deepEqual(saved.body.weights, {cast: 'off', theme: 'max'});
    html = (await step(env, a, {get: '/api/screen/recommend'})).body.body_html;
    assert.match(html, /いまは<b>作品の内容強め／出演者なし<\/b>/);
    assert.match(html, /<div class="wrow off" data-grp="cast">/);
    assert.doesNotMatch(html, /<span class="net">人物<\/span>出演 /);   // the cast leaves the reasons too
    const all = Object.fromEntries(['cast', 'author', 'craft', 'stage', 'produce', 'other', 'theme'].map(k => [k, 'off']));
    assert.equal((await step(env, a, {post: '/api/weight', body: {weights: all}})).status, 200);
    assert.match((await step(env, a, {get: '/api/screen/recommend'})).body.body_html, /<h1>今週のおすすめはありません<\/h1>/);
    // Only the listed groups and steps; nothing is written when one is wrong.
    assert.equal((await step(env, a, {post: '/api/weight', body: {weights: {cast: 'mid', bogus: 'max'}}})).status, 400);
    assert.equal((await step(env, a, {post: '/api/weight', body: {weights: {cast: '9'}}})).status, 400);
    assert.equal(sqlite.prepare("SELECT step FROM rank_weight WHERE grp='cast'").get().step, 'off');
    // Back to ふつう brings it back; another user is never affected.
    await step(env, a, {post: '/api/weight', body: {weights: Object.fromEntries(Object.keys(all).map(k => [k, 'mid']))}});
    assert.match((await step(env, a, {get: '/api/screen/recommend'})).body.body_html, /<h1>今週のおすすめ 1 件<\/h1>/);
    assert.match((await step(env, b, {get: '/api/screen/recommend'})).body.body_html, /すべて「ふつう」/);
    // The rest of the screen's writes answer as the public Python service does.
    const visit = await step(env, a, {post: '/api/recommendation/visit', body: {stage_id: '101'}});
    assert.equal(visit.status, 200); assert.equal(visit.body.disabled, true);
    const theme = await step(env, a, {post: '/api/hand_theme', body: {stage_id: '101', words: 'x'}});
    assert.equal(theme.status, 400); assert.match(theme.body.error, /公開版では公演情報の編集はできません/);
  } finally { sqlite.close(); }
});

// 2026-10-15 起案者「一回その案にしてみて」（q-interest-seed）: 興味ありを押した公演は、お気に入りと同じ
// 仮の ◎ になる。観た記録が無くても、一覧（catalogue）にだけある公演の出演欄からでも推薦が出る。
test('興味あり alone, on a stage only the catalogue has, recommends the same people; 興味なし later takes it back', async () => {
  const {env, sqlite} = await withIndex();
  const a = await signIn(env), b = await signIn(env);
  try {
    sqlite.prepare("INSERT INTO catalogue(id,title,date,venue,url,metadata) VALUES('779','気になる新作','2026-12-01','劇場Z','',?)")
      .run(JSON.stringify({end_date: '2026-12-05', fields: {出演: '俳優甲'}}));
    assert.equal((await step(env, a, {post: '/api/react', body: {stage_id: '779', value: 'interest', nofill: true}})).status, 200);
    const html = (await step(env, a, {get: '/api/screen/recommend'})).body.body_html;
    assert.match(html, /<article class="ticket recommend" data-stage="101"/);
    assert.match(html, /出演 <b>俳優甲<\/b><span class="n">（『気になる新作』）<\/span>/);
    // diag: what fed the recommendations (the JSON only, for checking production).
    const diag = (await step(env, a, {get: '/api/screen/recommend'})).body.diag;
    assert.deepEqual({i: diag.interest, p: diag.interest_with_people, r: diag.rated}, {i: 1, p: 1, r: 0});
    assert.ok(diag.ranked >= 1);
    assert.doesNotMatch(html, /履歴 0 本/);
    assert.doesNotMatch((await step(env, b, {get: '/api/screen/recommend'})).body.body_html, /<article/);
    // The newest answer per stage counts (reaction keeps one row per day).
    env.CLOCK = {today: env.CLOCK.today, now: env.CLOCK.now + 864e5 + 1000};
    sqlite.exec("UPDATE reaction SET label='2000-01-01'");
    assert.equal((await step(env, a, {post: '/api/react', body: {stage_id: '779', value: 'nointerest', nofill: true}})).status, 200);
    assert.doesNotMatch((await step(env, a, {get: '/api/screen/recommend'})).body.body_html, /<article/);
  } finally { sqlite.close(); }
});

// #116: a record dated after today (a plan, a typo) is not a rating to learn from yet.
test('a rating on a record dated after today is not learnt from until the day comes', async () => {
  const {env, sqlite} = await withIndex();
  const a = await signIn(env);
  try {
    const k1 = await rateSeen(env, a, '終わった舞台', '2026-08-05', '103', '◎');
    await rateSeen(env, a, '一日だけの舞台', '2026-09-05', '104', '×');
    const count = async () => (await step(env, a, {get: '/api/screen/recommend'})).body.diag.rated;
    assert.equal(await count(), 2);
    sqlite.prepare("UPDATE works SET first_date='2099-01-01', last_date='2099-01-01', updated_at='2099-01-01 00:00:00' WHERE work_key=?").run(k1);
    assert.equal(await count(), 1);
    sqlite.prepare("UPDATE works SET first_date=?, last_date=?, updated_at='2099-01-02 00:00:00' WHERE work_key=?").run(env.CLOCK.today, env.CLOCK.today, k1);
    assert.equal(await count(), 2, 'seen today counts');
  } finally { sqlite.close(); }
});

// #119: GET /api/recommend is the screen's ranking (same input, same rules, same cache row), as data.
test('/api/recommend answers with the 今週のおすすめ ranking and shares its cache; migration-era records do not feed it', async () => {
  const {env, sqlite} = await withIndex();
  const a = await signIn(env);
  try {
    await rateSeen(env, a, '終わった舞台', '2026-08-05', '103', '◎');
    await rateSeen(env, a, '一日だけの舞台', '2026-09-05', '104', '×');
    const screen = await step(env, a, {get: '/api/screen/recommend'});
    const shown = [...screen.body.body_html.matchAll(/<article class="ticket recommend" data-stage="(\d+)"/g)].map(m => m[1]);
    assert.ok(shown.length >= 1);
    const stamp = sqlite.prepare('SELECT stamp FROM rec_cache').get().stamp;
    const api = await step(env, a, {get: '/api/recommend'});
    assert.equal(api.status, 200);
    assert.equal(api.body.ready, true);
    assert.equal(api.body.cached, true, 'the screen\'s cached ranking, not a second computation');
    assert.equal(sqlite.prepare('SELECT stamp FROM rec_cache').get().stamp, stamp, 'the cache row is not overwritten');
    assert.match(api.body.recommender, /^screen-v\d+\|/);
    assert.deepEqual(api.body.items.map(i => i.stage_id), shown);
    assert.equal(api.body.n_rated, 2);
    assert.deepEqual(api.body.items[0].reasons[0], {role: '出演', person: '俳優甲', n: 1});
    assert.ok(api.body.items[0].title);
    // An answer on the screen reaches it at once.
    assert.equal((await step(env, a, {post: '/api/react', body: {stage_id: shown[0], value: 'nointerest', nofill: true}})).status, 200);
    assert.ok(!(await step(env, a, {get: '/api/recommend'})).body.items.some(i => i.stage_id === shown[0]));
    // The migration-era store (/api/record, records) is not an input of the recommendations any more.
    const before = (await step(env, a, {get: '/api/recommend'})).body.items.map(i => i.stage_id);
    assert.equal((await step(env, a, {post: '/migration-api/record', body: {id: 'm1', title: 't', date: '2026-08-01', rating: '◎', stage_id: '104'}})).status, 200);
    assert.deepEqual((await step(env, a, {get: '/api/recommend'})).body.items.map(i => i.stage_id), before);
  } finally { sqlite.close(); }
});

// #112: the time a rating was made is kept apart from later edits of the 感想.
test('editing only the 感想 keeps the time the rating was made; a new rating or 詳細 moves it', async () => {
  const {env, sqlite} = await withIndex();
  const a = await signIn(env);
  try {
    const key = await rateSeen(env, a, '終わった舞台', '2026-08-05', '103', '◎');
    const at = () => sqlite.prepare('SELECT rated_at, updated_at FROM works WHERE work_key=?').get(key);
    const first = at();
    assert.ok(first.rated_at);
    const later = () => { env.CLOCK = {today: env.CLOCK.today, now: env.CLOCK.now + 3600e3}; };
    later();
    assert.equal((await step(env, a, {post: '/api/note', body: {work_key: key, note_impression: '家族の描写がよかった'}})).status, 200);
    assert.equal(at().rated_at, first.rated_at);
    assert.notEqual(at().updated_at, first.updated_at);
    later();
    assert.equal((await step(env, a, {post: '/api/rate', body: {work_key: key, verdict: '◎'}})).status, 200);
    assert.equal(at().rated_at, first.rated_at, 'the same rating again is not a new one');
    later();
    assert.equal((await step(env, a, {post: '/api/rate', body: {work_key: key, aspects: '+acting'}})).status, 200);
    const third = at().rated_at;
    assert.ok(third > first.rated_at, '詳細 is part of the rating');
    later();
    assert.equal((await step(env, a, {post: '/api/rate', body: {work_key: key, verdict: '○'}})).status, 200);
    assert.ok(at().rated_at > third);
  } finally { sqlite.close(); }
});

// #110: the answer copied to the tour's other venues is the same one press, not more interest.
test('興味あり copied to the tour\'s other venues counts once as a hint; a venue pressed again directly counts', async () => {
  const {env, sqlite} = await withIndex();
  const a = await signIn(env);
  try {
    const ins = sqlite.prepare("INSERT INTO catalogue(id,title,date,venue,url,metadata) VALUES(?,'気になるツアー','2026-12-01',?,'',?)");
    for (const [id, v] of [['781', '劇場A'], ['782', '劇場B'], ['783', '劇場C']]) ins.run(id, v, JSON.stringify({end_date: '2026-12-05', fields: {出演: '俳優甲'}}));
    assert.equal((await step(env, a, {post: '/api/react', body: {stage_id: '781', value: 'interest', nofill: true, siblings: ['782', '783']}})).status, 200);
    assert.equal(sqlite.prepare("SELECT count(*) AS n FROM reaction WHERE source='screen_tour'").get().n, 2, 'the venues keep their copy');
    const diag = (await step(env, a, {get: '/api/screen/recommend'})).body.diag;
    assert.deepEqual({i: diag.interest, p: diag.interest_with_people}, {i: 1, p: 1});
    // Pressed again on another venue by the user themself: that one is an answer of its own.
    env.CLOCK = {today: env.CLOCK.today, now: env.CLOCK.now + 864e5 + 1000};
    sqlite.exec("UPDATE reaction SET label='2000-01-01'");
    assert.equal((await step(env, a, {post: '/api/react', body: {stage_id: '782', value: 'interest', nofill: true}})).status, 200);
    assert.equal((await step(env, a, {get: '/api/screen/recommend'})).body.diag.interest, 2);
  } finally { sqlite.close(); }
});

test('a person raised only by pseudo ratings is not shown as 履歴 0 本', async () => {
  const {reasonRows} = await import('../src/screens/recommend.js');
  const html = reasonRows({parts: [[0.5, '脚本', '家丁', 0]], kinds: []}, new Map());
  assert.match(html, /脚本 <b>家丁<\/b><span class="n">（お気に入り・興味ありの公演から）<\/span>/);
});

// 起案者の質問 2026-10-16「おすすめ画面では理由がちゃんと出てるのに、興味ありに移ったらおすすめ理由が空欄になるのなんで？」
test('興味あり pressed on おすすめ keeps the reasons it was shown with, and the 興味あり list shows them', async () => {
  const {env, sqlite} = await withIndex();
  const a = await signIn(env);
  try {
    await rateSeen(env, a, '終わった舞台', '2026-08-05', '103', '◎');
    await rateSeen(env, a, '一日だけの舞台', '2026-09-05', '104', '×');
    const reason = /<li class="rs b"><span class="net">人物<\/span>出演 <b>俳優甲<\/b><span class="n">（『終わった舞台』）<\/span>/;
    assert.match((await step(env, a, {get: '/api/screen/recommend'})).body.body_html, reason);
    assert.equal((await step(env, a, {post: '/api/react', body: {stage_id: '101', value: 'interest', nofill: true, siblings: []}})).status, 200);
    assert.match(sqlite.prepare("SELECT why FROM reaction WHERE stage_id='101'").get().why, /俳優甲/);
    const html = (await step(env, a, {get: '/api/screen/interest'})).body.body_html;
    assert.match(html, /data-stage="101"/);
    assert.match(html, reason);
    assert.doesNotMatch(html, /理由を出せていません/);
    // A 興味あり from before the reasons were kept: the reasons come from the cache, without the stage's own title.
    sqlite.exec("UPDATE reaction SET why=NULL");
    const old = (await step(env, a, {get: '/api/screen/interest'})).body.body_html;
    assert.match(old, reason);
  } finally { sqlite.close(); }
});

test('a kept reason with a price band does not show it', async () => {
  const {reasonRows} = await import('../src/screens/recommend.js');
  const html = reasonRows({parts: [], kinds: [[1, '#値段', '〜5000円', 1], [1, '#形式', 'ミュージカル', 1]]}, new Map());
  assert.doesNotMatch(html, /値段|5000/);
  assert.match(html, /ミュージカル/);
});

// 起案者の指示 2026-10-16「おすすめ理由に2.5次元として出してほしい。いらない人はそれ✕押せばいい」
test('a genre turned off with ✕ takes its stages out of the recommendations', async () => {
  const {env, sqlite} = await withIndex();
  const a = await signIn(env);
  try {
    await rateSeen(env, a, '終わった舞台', '2026-08-05', '103', '◎');
    await rateSeen(env, a, '一日だけの舞台', '2026-09-05', '104', '×');
    const ver = sqlite.prepare("SELECT v FROM rec_meta WHERE k='current'").get().v;
    sqlite.prepare("INSERT INTO rec_credit(ver,role,person,stage_id,role_w,role_group) VALUES(?,'#ジャンル','2.5次元','101',1,'theme')").run(ver);
    assert.match((await step(env, a, {get: '/api/screen/recommend'})).body.body_html, /data-stage="101"/);
    assert.equal((await step(env, a, {post: '/api/kind_off', body: {action: 'add', key: '#ジャンル\t2.5次元'}})).status, 200);
    assert.doesNotMatch((await step(env, a, {get: '/api/screen/recommend'})).body.body_html, /data-stage="101"/);
    // ✕ で戻すと、また出る
    assert.equal((await step(env, a, {post: '/api/kind_off', body: {action: 'remove', key: '#ジャンル\t2.5次元'}})).status, 200);
    assert.match((await step(env, a, {get: '/api/screen/recommend'})).body.body_html, /data-stage="101"/);
  } finally { sqlite.close(); }
});
