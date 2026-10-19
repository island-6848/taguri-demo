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
    assert.equal(got.body.title, '今週のあなたへのおすすめ');
    assert.equal(got.body.moving, undefined);
    assert.match(got.body.body_html, /<h1>今週のあなたへのおすすめはありません<\/h1>/);
    assert.doesNotMatch(got.body.body_html, /<article/);
    // 推薦を出すためのワンポイント (起案者 2026-10-14): what to do, in plain words.
    assert.match(got.body.body_html, /<h2>おすすめを出すためのワンポイント<\/h2>/);
    assert.match(got.body.body_html, /<b>過去の観劇記録を2件以上追加する<\/b>/);
    assert.match(got.body.body_html, /<a href="\/register\?t=__TAGURI_TOKEN__">観劇記録を追加<\/a>/);
    assert.match(got.body.body_html, /<p class="tip-or">または<\/p>[\s\S]*「お気に入り」に登録する[\s\S]*<p class="tip-or">または<\/p>[\s\S]*「開幕リマインド」で興味あり・なしを回答する/);
    assert.match(got.body.body_html, /<svg class="tip-art"/);
    // 使い始めでおすすめが無いときは、選び方と絞り込みを出さない（起案者 2026-10-18）
    assert.doesNotMatch(got.body.body_html, /おすすめの選び方|表示の絞り込み|class="fil2/);
    assert.doesNotMatch(got.body.body_html, /favnone/);   // お気に入りが無い人には一文を出さない
  } finally { sqlite.close(); }
});

test('a ◎ on a stage recommends the coming stage of the same people, with the Python card and the reasons', async () => {
  const {env, sqlite} = await withIndex();
  const a = await signIn(env), b = await signIn(env);
  try {
    await rateSeen(env, a, '終わった舞台', '2026-08-05', '103', '◎');
    await rateSeen(env, a, '一日だけの舞台', '2026-09-05', '104', '×');
    const html = (await step(env, a, {get: '/api/screen/recommend'})).body.body_html;
    assert.match(html, /<h1>今週のあなたへのおすすめ 1 件<\/h1>/);
    assert.match(html, /<article class="ticket recommend" data-stage="101"/);
    assert.doesNotMatch(html, /おすすめを出すためのワンポイント/);
    assert.match(html, /おすすめの選び方/);
    assert.match(html, /表示の絞り込み/);
    assert.match(html, /<span class="sn">No\.01<\/span>/);
    assert.match(html, /<li class="rs b"><span class="net">人物<\/span>出演 <a class="rsl"[^>]*><b>俳優甲<\/b><\/a><span class="n">（『終わった舞台』）<\/span>/);
    assert.doesNotMatch(html, /<!--(rank|why|poster)-->/);
    assert.match(html, /<button data-v="interest">興味あり<\/button>/);
    // The other user sees none of it.
    assert.doesNotMatch((await step(env, b, {get: '/api/screen/recommend'})).body.body_html, /<article/);
    // Prefecture filter: ?f=1 holds it for this page only (not saved), an empty ?f=1 is 全国.
    const osaka = (await step(env, a, {get: '/api/screen/recommend?f=1&pref=' + encodeURIComponent('大阪府')})).body.body_html;
    assert.match(osaka, /<h1>大阪府でのあなたへのおすすめはありません<\/h1>/);
    assert.match((await step(env, a, {get: '/api/screen/recommend'})).body.body_html, /いまは<b>全国<\/b>/);
    assert.equal(sqlite.prepare("SELECT count(*) AS n FROM app_setting WHERE key='recommend_prefs'").get().n, 0);
    const tokyo = (await step(env, a, {get: '/api/screen/recommend?f=1&pref=' + encodeURIComponent('東京都')})).body.body_html;
    assert.match(tokyo, /<h1>東京都でのあなたへのおすすめ 1 件<\/h1>/);
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
    assert.match(doneHtml, /<h1>今週のあなたへのおすすめにはすべて答えました<\/h1>/);
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
    // 保存していない人は群ごとの初めの設定（起案者の指示 2026-10-18「出演者、作品の内容︰少し強く／制作・宣伝、その他の役職︰
    // あまり効かせない／それ以外はふつう」）。前は全部「ふつう」だった
    assert.match(html, /いまは<b>出演者・作品の内容強め／制作・宣伝・その他の役職弱め<\/b>/);
    assert.match(html, /<div class="wrow" data-grp="cast"><span class="wl">出演者<\/span><span class="wn">おすすめの候補 1 件で一致<\/span>/);
    assert.match(html, /value="3" data-weight="cast" data-default="strong"[^>]*><span class="wv">少し強く<\/span>/);
    assert.match(html, /value="3" data-weight="theme" data-default="strong"/);
    assert.match(html, /value="1" data-weight="produce" data-default="weak"/);
    assert.match(html, /value="1" data-weight="other" data-default="weak"/);
    assert.match(html, /value="2" data-weight="author" data-default="mid"/);
    assert.match(html, /<button class="pall-btn" data-wreset="1">すべて初めの設定に戻す<\/button>/);
    assert.match(html, /<h1>今週のあなたへのおすすめ 1 件<\/h1>/);
    const saved = await step(env, a, {post: '/api/weight', body: {weights: {cast: 'off', theme: 'max'}}});
    assert.equal(saved.status, 200);
    assert.deepEqual(saved.body.weights, {cast: 'off', theme: 'max'});
    html = (await step(env, a, {get: '/api/screen/recommend'})).body.body_html;
    assert.match(html, /いまは<b>作品の内容強め／制作・宣伝・その他の役職弱め／出演者なし<\/b>/);
    assert.match(html, /<div class="wrow off" data-grp="cast">/);
    assert.doesNotMatch(html, /<span class="net">人物<\/span>出演 /);   // the cast leaves the reasons too
    const all = Object.fromEntries(['cast', 'author', 'craft', 'stage', 'produce', 'other', 'theme'].map(k => [k, 'off']));
    assert.equal((await step(env, a, {post: '/api/weight', body: {weights: all}})).status, 200);
    assert.match((await step(env, a, {get: '/api/screen/recommend'})).body.body_html, /<h1>今週のあなたへのおすすめはありません<\/h1>/);
    // Only the listed groups and steps; nothing is written when one is wrong.
    assert.equal((await step(env, a, {post: '/api/weight', body: {weights: {cast: 'mid', bogus: 'max'}}})).status, 400);
    assert.equal((await step(env, a, {post: '/api/weight', body: {weights: {cast: '9'}}})).status, 400);
    assert.equal(sqlite.prepare("SELECT step FROM rank_weight WHERE grp='cast'").get().step, 'off');
    // Back to ふつう brings it back; another user is never affected.
    await step(env, a, {post: '/api/weight', body: {weights: Object.fromEntries(Object.keys(all).map(k => [k, 'mid']))}});
    const back = (await step(env, a, {get: '/api/screen/recommend'})).body.body_html;
    assert.match(back, /<h1>今週のあなたへのおすすめ 1 件<\/h1>/);
    // 保存してある段は、初めの設定が変わってもそのまま（すべて「ふつう」で保存した人は「ふつう」）
    assert.match(back, /いまは<b>ふつう<\/b>/);
    assert.match(back, /value="2" data-weight="cast" data-default="strong"/);
    // B は効かせ方を何も変えていない（使い始めでおすすめが無いので、選び方を出さず、使い始めの案内を出す）
    const bHtml = (await step(env, b, {get: '/api/screen/recommend'})).body.body_html;
    assert.match(bHtml, /おすすめを出すためのワンポイント/);
    assert.doesNotMatch(bHtml, /id="weights"/);
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
    assert.match(html, /出演 <a class="rsl"[^>]*><b>俳優甲<\/b><\/a><span class="n">（『気になる新作』）<\/span>/);
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

// #196: 押した公演と同じ公演のほかの会場への答えは、まとめて保存するか、まったく保存しないか。
// 入れ替わりの 1 枚が作れなくても、保存できた答えを失敗とは返さない（fill: null と、取り直せる印）
function faultyDb(env, fails) {
  const orig = env.DB.prepare, state = {saved: false};
  const wrapSt = (st, sql, args = []) => {
    const go = async (m, isWrite) => {
      if (fails(sql, args, state)) throw new Error('injected D1 failure');
      const r = await st[m]();
      if (isWrite && /INSERT INTO reaction/.test(sql)) state.saved = true;
      return r;
    };
    return {bind: (...v) => wrapSt(st.bind(...v), sql, v), first: () => go('first'), all: () => go('all'), run: () => go('run', true), execute: () => go('execute', true)};
  };
  env.DB.prepare = sql => wrapSt(orig(sql), sql);
  return () => { env.DB.prepare = orig; };
}
test('an answer and its copies to the other venues are saved together or not at all; a failed fill still reports the save', async () => {
  const {env, sqlite} = await withIndex();
  const a = await signIn(env);
  try {
    const ins = sqlite.prepare("INSERT INTO catalogue(id,title,date,venue,url,metadata) VALUES(?,'気になるツアー','2026-12-01',?,'',?)");
    for (const [id, v] of [['781', '劇場A'], ['782', '劇場B'], ['783', '劇場C']]) ins.run(id, v, JSON.stringify({end_date: '2026-12-05', fields: {出演: '俳優甲'}}));
    const count = () => sqlite.prepare("SELECT count(*) AS n FROM reaction WHERE stage_id IN ('781','782','783')").get().n;
    // 3 つめの会場の保存で失敗: 押した公演も 2 つめの会場も残さない（応答の失敗と保存の結果が合う）
    let restore = faultyDb(env, (sql, args) => /INSERT INTO reaction/.test(sql) && args.includes('783'));
    const broken = await step(env, a, {post: '/api/react', body: {stage_id: '781', value: 'interest', nofill: true, siblings: ['782', '783']}});
    restore();
    assert.notEqual(broken.status, 200);
    assert.equal(count(), 0, 'nothing is saved when one venue fails');
    // 保存のあと、入れ替わりの 1 枚を作る読み取りで失敗: 保存できたと返し、fill は null（取り直せる）
    restore = faultyDb(env, (sql, args, st) => st.saved && !/INSERT INTO reaction/.test(sql));
    const got = await step(env, a, {post: '/api/react', body: {stage_id: '781', value: 'interest', siblings: ['782', '783'], shown: ['781']}});
    restore();
    assert.equal(got.status, 200);
    assert.deepEqual({ok: got.body.ok, saved: got.body.saved, fill: got.body.fill, retry: got.body.fill_status}, {ok: true, saved: true, fill: null, retry: 'retry_available'});
    assert.equal(count(), 3);
  } finally { sqlite.close(); }
});

// 起案者の指示 2026-10-18「おすすめ理由に『（お気に入り・興味ありの公演から）』って書くのやめて。ちゃんと公演タイトル書いて」:
// 作品名の引けない人は何も添えない（前は「（お気に入り・興味ありの公演から）」と書いていた）
test('a person raised only by pseudo ratings is not shown as 履歴 0 本, nor as （お気に入り・興味ありの公演から）', async () => {
  const {reasonRows} = await import('../src/screens/recommend.js');
  // 括弧の説明を書けない行は出さない（起案者の問い 2026-10-18「括弧でおすすめ理由がついてないものがおすすめ理由に出ちゃってる。
  // なぜ？」で仕様が変わった。前は名前だけの行「脚本 家丁」を出すのが期待だった。fix-reason-no-paren）
  const html = reasonRows({parts: [[0.5, '脚本', '家丁', 0]], kinds: []}, new Map());
  assert.doesNotMatch(html, /家丁/);
  assert.match(html, /理由を出せていません/);
  assert.doesNotMatch(html, /お気に入り・興味ありの公演から|履歴 0 本/);
});

// 同じ日の指示「公演タイトルすでに書けているものも、最大2件だけ表示。一番最近の公演と一番古い公演から計2個」
test('a reason names only the newest and the oldest work', async () => {
  const {reasonRows} = await import('../src/screens/recommend.js');
  const titles = new Map([['出演\t甲', ['新', '中', '古']], ['演出\t乙', ['一つ']], ['脚本\t丙', ['二', '一']]]);
  const html = reasonRows({parts: [[0.5, '出演', '甲', 3], [0.4, '演出', '乙', 1], [0.3, '脚本', '丙', 2]], kinds: []}, titles);
  assert.match(html, /出演 <a class="rsl"[^>]*><b>甲<\/b><\/a><span class="n">（『新』・『古』 ほか 1 本）<\/span>/);
  assert.match(html, /演出 <a class="rsl"[^>]*><b>乙<\/b><\/a><span class="n">（『一つ』）<\/span>/);
  assert.match(html, /脚本 <a class="rsl"[^>]*><b>丙<\/b><\/a><span class="n">（『二』・『一』）<\/span>/);
  assert.doesNotMatch(html, /『中』/);
});

// お気に入りの名前から引いた公演の共演者も、その公演の題名で書く（前は「（お気に入り・興味ありの公演から）」）
test('a co-worker of a favourite is named with the favourite\'s work', async () => {
  const {env, sqlite} = await withIndex();
  const a = await signIn(env);
  try {
    await rateSeen(env, a, '終わった舞台', '2026-08-05', '103', '◎');
    await rateSeen(env, a, '一日だけの舞台', '2026-09-05', '104', '×');
    // 作家丁の公演（102 舞台ふたつめ、初日 2026-10-01）に出ている俳優乙が、101 の理由になる
    assert.equal((await step(env, a, {post: '/api/favourite', body: {action: 'add', kind: '人', name: '作家丁'}})).status, 200);
    const html = (await step(env, a, {get: '/api/screen/recommend'})).body.body_html;
    assert.match(html, /data-stage="101"/);
    // 評価の履歴の無い人は、登録した名前と、その公演の題名で書く（起案者の指示 2026-10-18「理由の文は、登録した名前を書く」。
    // 前は「（『舞台ふたつめ』）」だけで、だれのお気に入りから来たのか分からなかった）
    // 起案者の指示 2026-10-18「『お気に入りの横山拓也と同じ公演に関わる人：『雉はじめて鳴く』』→『横山拓也 演出『雉はじめて鳴く』出演』」で
    // 理由の形が変わったので、期待を「登録した名前 その作品での役職『作品名』この人のその作品での役職」に直した（fix-fav-reason-roles）
    assert.match(html, /出演 <a class="rsl"[^>]*><b>俳優乙<\/b><\/a><span class="n">（作家丁 脚本『舞台ふたつめ』出演）<\/span>/);
    // 種類の理由も、新しい公演（初日 10/01）→ 古い公演（観た日 08/05）の順
    assert.match(html, /<span class="net">形式<\/span>原作 <a class="rsl"[^>]*><b>オリジナル<\/b><\/a><span class="n">（『舞台ふたつめ』・『終わった舞台』）<\/span>/);
    assert.doesNotMatch(html, /お気に入り・興味ありの公演から/);
  } finally { sqlite.close(); }
});

// 起案者の質問 2026-10-16「おすすめ画面では理由がちゃんと出てるのに、興味ありに移ったらおすすめ理由が空欄になるのなんで？」
test('興味あり pressed on おすすめ keeps the reasons it was shown with, and the 興味あり list shows them', async () => {
  const {env, sqlite} = await withIndex();
  const a = await signIn(env);
  try {
    await rateSeen(env, a, '終わった舞台', '2026-08-05', '103', '◎');
    await rateSeen(env, a, '一日だけの舞台', '2026-09-05', '104', '×');
    const reason = /<li class="rs b"><span class="net">人物<\/span>出演 <a class="rsl"[^>]*><b>俳優甲<\/b><\/a><span class="n">（『終わった舞台』）<\/span>/;
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

// #138: 裏の答え合わせ（chooseVariant）は評価だけで決まるので、評価が変わらないまま控えが捨てられたとき
// （お気に入り・興味ありを足した）は前の結果を使い直す。使い直しても、計算し直しても、同じ一覧になる
test('the hidden check is reused while the ratings are unchanged, with the same ranking as a fresh run', async () => {
  const {env, sqlite} = await withIndex();
  const a = await signIn(env);
  try {
    const uid = sqlite.prepare('SELECT id FROM users ORDER BY created_at DESC LIMIT 1').get().id;
    const sids = sqlite.prepare("SELECT stage_id FROM rec_people WHERE ver=(SELECT v FROM rec_meta WHERE k='current') ORDER BY stage_id").all().map(r => r.stage_id);
    const ins = sqlite.prepare('INSERT INTO works(user_id,work_key,title,first_date,last_date,times,verdict,stage_id,updated_at,rated_at) VALUES(?,?,?,?,?,1,?,?,?,?)');
    for (let i = 0; i < 36; i++) ins.run(uid, `g${i}`, `作品${i}`, '2025-01-01', '2025-01-01', `${1 + (i * 7) % 5}/5`, sids[i % sids.length], `2025-01-01 00:00:${String(i).padStart(2, '0')}`, `2025-01-01 00:00:${String(i).padStart(2, '0')}`);
    const html = async () => (await step(env, a, {get: '/api/screen/recommend'})).body.body_html;
    await html();
    const first = JSON.parse(sqlite.prepare('SELECT body FROM rec_cache WHERE user_id=?').get(uid).body).gate;
    assert.ok(first && first.key && first.choice && first.choice.multipliers);
    sqlite.prepare("INSERT INTO favourites(user_id,name,kind) VALUES(?,?,?)").run(uid, '架空の人', '人');   // 控えは捨てられるが評価は同じ
    const reused = await html();
    assert.equal(JSON.parse(sqlite.prepare('SELECT body FROM rec_cache WHERE user_id=?').get(uid).body).gate.key, first.key);
    sqlite.prepare('DELETE FROM rec_cache WHERE user_id=?').run(uid);
    assert.equal(await html(), reused);
    // 評価が変われば計算し直す（鍵が変わる）
    sqlite.prepare("UPDATE works SET verdict='5/5', updated_at='2025-02-01 00:00:00' WHERE user_id=? AND work_key='g0'").run(uid);
    await html();
    assert.notEqual(JSON.parse(sqlite.prepare('SELECT body FROM rec_cache WHERE user_id=?').get(uid).body).gate.key, first.key);
  } finally { sqlite.close(); }
});
