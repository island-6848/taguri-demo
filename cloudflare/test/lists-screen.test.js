// 興味あり・お気に入り・購入済み on the Worker (screens/lists.js) and their writes.
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
const screen = async (env, u, name, q = '') => (await step(env, u, {get: `/api/screen/${name}${q}`})).body;

test('a new account has empty lists', async () => {
  const {env, sqlite} = withIndex();
  const a = await signIn(env);
  try {
    assert.match((await screen(env, a, 'interest')).body_html, /<h1>追いかけている 0 件<\/h1>[\s\S]*追いかけている公演はありません/);
    const fav = (await screen(env, a, 'favourites')).body_html;
    assert.match(fav, /<h1>お気に入り ── 新着 0 件<\/h1>/);
    assert.match(fav, /<details class="pbox" id="names" open>/);
    assert.match((await screen(env, a, 'tickets')).body_html, /<h1>購入済み公演 ── 0 件<\/h1>/);
  } finally { sqlite.close(); }
});

test('興味あり lists what was answered "interest", with the note; other users see nothing', async () => {
  const {env, sqlite} = withIndex();
  const a = await signIn(env), b = await signIn(env);
  try {
    assert.equal((await step(env, a, {post: '/api/react', body: {stage_id: '101', value: 'interest', nofill: true}})).status, 200);
    assert.equal((await step(env, a, {post: '/api/react', body: {stage_id: '101', note: '俳優甲 & 乙'}})).status, 200);
    const html = (await screen(env, a, 'interest')).body_html;
    assert.match(html, /<h1>追いかけている 1 件<\/h1>/);
    assert.match(html, /<article class="ticket interest" data-stage="101"/);
    assert.match(html, /<span class="wnt">俳優甲 &amp; 乙<\/span>/);
    assert.match(html, /回答を変える/);
    assert.match(html, /<nav class="idx" aria-label="月で切り替える">/);
    assert.match((await screen(env, b, 'interest')).body_html, /追いかけている 0 件/);
    // Not interested: out of 興味あり.
    await step(env, a, {post: '/api/react', body: {stage_id: '101', value: 'nointerest', nofill: true}});
    assert.match((await screen(env, a, 'interest')).body_html, /追いかけている 0 件/);
  } finally { sqlite.close(); }
});

test('a registered name brings its stages to お気に入り and out of おすすめ', async () => {
  const {env, sqlite} = withIndex();
  const a = await signIn(env);
  try {
    const add = await step(env, a, {post: '/api/favourite', body: {action: 'add', kind: '人', name: '俳優甲'}});
    assert.equal(add.status, 200);
    assert.equal(add.body.n, 1);
    const fav = (await screen(env, a, 'favourites')).body_html;
    assert.match(fav, /<h1>お気に入り ── 新着 1 件<\/h1>/);
    assert.match(fav, /<article class="ticket favourite" data-stage="101"/);
    assert.match(fav, /登録した人「俳優甲」の公演です/);
    assert.match(fav, /<span class="tgn">人「俳優甲」<\/span>/);
    assert.doesNotMatch(fav, /data-v="interest"/);                 // read only
    // Group names match the producing company only.
    await step(env, a, {post: '/api/favourite', body: {action: 'add', kind: '団体', name: '劇団乙'}});
    assert.match((await screen(env, a, 'favourites')).body_html, /新着 2 件[\s\S]*data-stage="102"/);
    await step(env, a, {post: '/api/favourite', body: {action: 'remove', kind: '団体', name: '劇団乙'}});
    assert.match((await screen(env, a, 'favourites')).body_html, /新着 1 件/);
    // おすすめ leaves it out even when the ratings would raise it.
    for (const [t, d, sid, v] of [['終わった舞台', '2026-08-05', '103', '◎'], ['一日だけの舞台', '2026-09-05', '104', '×']]) {
      const key = (await step(env, a, {post: '/api/add_work', body: {title: t, date: d}})).body.work_key;
      await step(env, a, {post: '/api/link_stage', body: {work_key: key, stage_id: sid}});
      await step(env, a, {post: '/api/rate', body: {work_key: key, verdict: v}});
    }
    assert.doesNotMatch((await screen(env, a, 'recommend')).body_html, /data-stage="101"/);
    assert.equal((await step(env, a, {post: '/api/favourite', body: {action: 'add', kind: '星', name: 'x'}})).status, 400);
    // 出さない語
    assert.equal((await step(env, a, {post: '/api/decline', body: {action: 'add', word: 'バレエ'}})).status, 200);
    assert.match((await screen(env, a, 'favourites')).body_html, /出さない語 <b>1 語<\/b>[\s\S]*「バレエ」/);
  } finally { sqlite.close(); }
});

test('購入済み shows owned stages with their tickets; an ended one moves to 未評価', async () => {
  const {env, sqlite} = withIndex();
  const a = await signIn(env);
  try {
    await step(env, a, {post: '/api/react', body: {stage_id: '101', value: 'owned', nofill: true}});
    assert.equal((await step(env, a, {post: '/api/ticket', body: {stage_id: '101', date: '2026-11-03', time: '14:00'}})).status, 200);
    assert.equal((await step(env, a, {post: '/api/ticket', body: {stage_id: '101', date: '2027-01-01'}})).status, 400);
    const html = (await screen(env, a, 'tickets')).body_html;
    assert.match(html, /<h1>購入済み公演 ── 1 件<\/h1>/);
    assert.match(html, /<article class="ticket owned" data-stage="101"/);
    assert.match(html, /<span class="mt-row">11月3日 14:00 <button data-mt-del="101" data-date="2026-11-03" data-time="14:00">取り消す<\/button><\/span>/);
    assert.match(html, /min="2026-11-01" max="2026-11-10"/);
    assert.doesNotMatch((await screen(env, a, 'interest')).body_html, /data-stage="101"/);
    // After the ticket's date the stage leaves 購入済み and waits for a rating.
    env.CLOCK = {today: '2026-11-04', now: Date.parse('2026-11-04T03:00:00Z')};
    assert.match((await screen(env, a, 'tickets')).body_html, /購入済み公演 ── 0 件/);
    assert.match((await screen(env, a, 'unrated')).body_html, /舞台ひとつめ/);
    assert.equal(sqlite.prepare("SELECT count(*) AS n FROM works WHERE stage_id='101'").get().n, 1);
    await screen(env, a, 'tickets');
    assert.equal(sqlite.prepare("SELECT count(*) AS n FROM works WHERE stage_id='101'").get().n, 1);
  } finally { sqlite.close(); }
});

test('開幕リマインド: every stage opening this week, with the shared prefecture filter', async () => {
  const {env, sqlite} = withIndex();
  const a = await signIn(env);
  try {
    env.CLOCK = {today: '2026-10-20', now: Date.parse('2026-10-20T03:00:00Z')};
    const html = (await screen(env, a, 'reminder')).body_html;
    assert.match(html, /<h1>開幕リマインド ── 見逃していませんか<\/h1>/);
    assert.match(html, /<nav class="idx" aria-label="週で切り替える">/);
    assert.match(html, /今週<span class="mn">0<\/span>/);
    assert.match(html, /来週<span class="mn">1<\/span>/);
    const next = (await screen(env, a, 'reminder', '?w=next')).body_html;
    assert.match(next, /<li class="dgli dgfold und" data-stage="101"><details class="dgopen"><summary>/);
    assert.match(next, /<input type="hidden" name="w" value="next">/);
    await step(env, a, {post: '/api/react', body: {stage_id: '101', value: 'interest', nofill: true}});
    assert.match((await screen(env, a, 'reminder', '?w=next')).body_html, /<li class="dgli dgfold trk" data-stage="101">/);
    // The filter chosen here applies to おすすめ too.
    await screen(env, a, 'reminder', '?w=next&f=1&pref=' + encodeURIComponent('大阪府'));
    assert.match((await screen(env, a, 'recommend')).body_html, /いまは<b>大阪府（1 県）<\/b>/);
  } finally { sqlite.close(); }
});

// 2026-10-14 起案者「開幕リマインドは推薦がなくても表示されるはずだけど、出ないのなんで？」:
// the index is replaced only on days it fits the write budget, so it can lack this
// week's openings; the catalogue (upserted daily) fills them in.
test('開幕リマインド also lists the catalogue openings that a stale index lacks, for a new account', async () => {
  const {env, sqlite} = withIndex();
  const a = await signIn(env);
  try {
    env.CLOCK = {today: '2026-10-20', now: Date.parse('2026-10-20T03:00:00Z')};
    sqlite.prepare("INSERT INTO catalogue(id,title,date,venue,url,metadata) VALUES('777','索引に無い新作 & 夜','2026-10-22','劇場Z','',?)")
      .run(JSON.stringify({end_date: '2026-10-30', group: '劇団Z'}));
    sqlite.prepare("INSERT INTO catalogue(id,title,date,venue,url,metadata) VALUES('778','終わった公演','2026-09-01','劇場Z','','{}')").run();
    const html = (await screen(env, a, 'reminder')).body_html;
    assert.match(html, /今週<span class="mn">1<\/span>/);
    assert.match(html, /<li class="dgli dgfold und" data-stage="777">[\s\S]*?索引に無い新作 &amp; 夜[\s\S]*?劇場Z/);
    assert.doesNotMatch(html, /終わった公演/);
    // A stage in both keeps the index's row (it has the prefecture).
    assert.equal((await screen(env, a, 'reminder', '?w=next')).body_html.match(/<li class="dgli[^"]*" data-stage="101">/g).length, 1);
  } finally { sqlite.close(); }
});

// 2026-10-14 起案者「開幕リマインドで『興味あり』押して、そのまま開いても 0 件になる」: a stage
// only in the catalogue (no prebuilt card) was answered but dropped from 興味あり and
// stayed 未回答 here. Rows fold by title and open to the credits and synopsis.
test('開幕リマインド: a catalogue-only stage keeps its answer, shows in 興味あり, and opens to its credits', async () => {
  const {env, sqlite} = withIndex();
  const a = await signIn(env);
  try {
    env.CLOCK = {today: '2026-10-20', now: Date.parse('2026-10-20T03:00:00Z')};
    sqlite.prepare("INSERT INTO catalogue(id,title,date,venue,url,metadata) VALUES('777','索引に無い新作','2026-10-22','劇場Z','https://example.com/z',?)")
      .run(JSON.stringify({end_date: '2026-10-30', group: '劇団Z', synopsis: '海辺の町の三姉妹の話。', fields: {出演: '山田太郎、鈴木花子'}}));
    const html = (await screen(env, a, 'reminder')).body_html;
    assert.match(html, /data-stage="777"><details class="dgopen"><summary>[\s\S]*?<\/summary><div class="dgdetail">[\s\S]*?山田太郎、鈴木花子[\s\S]*?海辺の町の三姉妹の話。/);
    await step(env, a, {post: '/api/react', body: {stage_id: '777', value: 'interest', nofill: true}});
    assert.match((await screen(env, a, 'reminder')).body_html, /<li class="dgli dgfold trk" data-stage="777">/);
    const it = (await screen(env, a, 'interest')).body_html;
    assert.match(it, /<h1>追いかけている 1 件<\/h1>/);
    assert.match(it, /<article class="ticket interest" data-stage="777"[\s\S]*?索引に無い新作[\s\S]*?山田太郎/);
  } finally { sqlite.close(); }
});

test('公演カレンダー shows the stages owned, followed and of a registered name', async () => {
  const {env, sqlite} = withIndex();
  const a = await signIn(env);
  try {
    assert.match((await screen(env, a, 'calendar')).body_html, /カレンダーに表示できる公演がありません/);
    await step(env, a, {post: '/api/react', body: {stage_id: '101', value: 'owned', nofill: true}});
    await step(env, a, {post: '/api/ticket', body: {stage_id: '101', date: '2026-11-03', time: '14:00'}});
    await step(env, a, {post: '/api/favourite', body: {action: 'add', kind: '団体', name: '劇団乙'}});
    const html = (await screen(env, a, 'calendar')).body_html;
    assert.match(html, /<h1>公演カレンダー<\/h1>/);
    assert.match(html, /<button type="button" class="addtk" data-open-dialog="tkdlg">/);
    assert.match(html, /<span class="bar own"[^>]*data-stage="101"/);
    assert.match(html, /<span class="bar fav[^"]*" data-stage="102"/);
    assert.match(html, /11\/3 14:00 に行きます/);
    const owned = (await screen(env, a, 'calendar', '?kind=owned')).body_html;
    assert.doesNotMatch(owned, /data-stage="102"/);
  } finally { sqlite.close(); }
});

test('設定・はじめる・登録, the default prefectures, 観ればよかった and the export', async () => {
  const {env, sqlite} = withIndex();
  const a = await signIn(env), b = await signIn(env);
  try {
    const set = (await screen(env, a, 'settings')).body_html;
    assert.match(set, /<h1>設定<\/h1>/);
    assert.match(set, /いまは全国/);
    assert.match(set, /<a href="\/account">アカウント<\/a>/);
    assert.match(set, /取り消した記録はありません/);
    // Every prefecture and region can be chosen, also with nothing recommended there yet
    // (2026-10-14 起案者「地方選ぶ機能が使えなくなってる」).
    assert.equal(set.match(/<input type="checkbox" name="pref"/g).length, 47);
    assert.equal(set.match(/class="prg" data-prefs=/g).length, 8);
    assert.match(set, /data-prefs="鳥取県 島根県 岡山県 広島県 山口県">中国地方/);
    // The default set here applies to おすすめ (until a filter is chosen there).
    assert.equal((await step(env, a, {post: '/api/pref_setting', body: {prefs: ['大阪府', '火星']}})).body.prefs.join(), '大阪府');
    assert.match((await screen(env, a, 'settings')).body_html, /いまは大阪府（1 県）/);
    assert.match((await screen(env, a, 'recommend')).body_html, /いまは<b>大阪府（1 県）<\/b>/);
    assert.equal((await step(env, a, {post: '/api/pref_setting', body: {prefs: 'x'}})).status, 400);
    // はじめる counts the registered names and the works.
    assert.match((await screen(env, a, 'start')).body_html, /見逃したくない名前を登録する（いま 0 件）/);
    await step(env, a, {post: '/api/favourite', body: {action: 'add', kind: '人', name: '俳優甲'}});
    const start = (await screen(env, a, 'start')).body_html;
    assert.match(start, /（いま 1 件）[\s\S]*済んでいます/);
    assert.match(start, /人「俳優甲」/);
    // 観ればよかった: looked up among the stages in D1.
    assert.equal((await step(env, a, {post: '/api/missed', body: {title: '舞台ひとつめ'}})).status, 200);
    assert.equal((await step(env, a, {post: '/api/missed', body: {title: '聞いたことのない舞台'}})).status, 200);
    const reg = (await screen(env, a, 'register')).body_html;
    assert.match(reg, /<h1>公演情報の登録<\/h1>/);
    assert.match(reg, /<span class="badge part">2 件<\/span>/);
    assert.match(reg, /一覧にはあったが、表示する枠に入らなかった<\/span><span class="w">舞台ひとつめ<\/span>[\s\S]*<span class="cl">出演<\/span><span class="cv">俳優甲、俳優乙<\/span>/);
    assert.match(reg, /取り込んだ公演の中に無かった<\/span><span class="w">聞いたことのない舞台/);
    assert.doesNotMatch((await screen(env, b, 'register')).body_html, /舞台ひとつめ/);
    // The export holds this user's rows only.
    const res = await (await import('../src/worker.js')).default.fetch(new Request('https://taguri.example/export.json', {headers: {cookie: a}}), env);
    assert.equal(res.status, 200);
    assert.match(res.headers.get('content-disposition'), /taguri-export\.json/);
    const out = JSON.parse(await res.text());
    assert.equal(out.missed.length, 2);
    assert.deepEqual(out.declared['人'], ['俳優甲']);
    assert.ok(out.missed.every(r => r.user_id === out.missed[0].user_id));
  } finally { sqlite.close(); }
});

test('探す: coming stages and works seen, by words and by month', async () => {
  const {env, sqlite} = withIndex();
  const a = await signIn(env);
  try {
    const empty = (await screen(env, a, 'search')).body_html;
    assert.match(empty, /<h1>探す<\/h1>/);
    assert.match(empty, /これから観られる公演 3 件と観た記録の両方から探します/);
    // A coming stage found by a cast name: the card with 「ヒットした箇所」 on top.
    const byName = (await screen(env, a, 'search', '?q=' + encodeURIComponent('俳優甲'))).body_html;
    assert.match(byName, /<h2>これから観られる公演 1 件<\/h2>/);
    assert.match(byName, /<div class="whyh top">[\s\S]*ヒットした箇所：<\/div><ul class="why top"><li class="rs found"><span class="net">出演<\/span>俳優甲<\/li><\/ul>/);
    assert.doesNotMatch(byName, /おすすめ理由/);
    assert.match(byName, /この名前を追いますか？[\s\S]*data-name="俳優甲"/);
    // A work seen, found by its title, with the rating buttons.
    const key = (await step(env, a, {post: '/api/add_work', body: {title: '終わった舞台', date: '2026-08-05'}})).body.work_key;
    await step(env, a, {post: '/api/link_stage', body: {work_key: key, stage_id: '103'}});
    const seen = (await screen(env, a, 'search', '?q=' + encodeURIComponent('終わった'))).body_html;
    assert.match(seen, /<h2>観た記録 1 件<\/h2>/);
    assert.match(seen, /<div class="hitwhy"><span class="hl">ヒットした箇所：<\/span><span class="hw">題名<\/span><\/div>/);
    // By month: the works seen in August 2026.
    assert.match((await screen(env, a, 'search', '?ym=2026-08')).body_html, /2026 年 8 月に観た記録 1 件/);
    // Nothing found: ask the next daily run.
    const none = (await screen(env, a, 'search', '?q=' + encodeURIComponent('存在しない公演'))).body_html;
    assert.match(none, /data-search-request="存在しない公演"/);
    assert.equal((await step(env, a, {post: '/api/search_request', body: {q: '存在しない公演', source: 'search'}})).status, 200);
    assert.match((await screen(env, a, 'search', '?q=' + encodeURIComponent('存在しない公演'))).body_html, /探すよう頼んであります/);
    assert.equal((await step(env, a, {post: '/api/search_request', body: {q: 'x'}})).status, 400);
  } finally { sqlite.close(); }
});

test('たどる: a name seen in two stages becomes a thread', async () => {
  const {env, sqlite} = withIndex();
  const a = await signIn(env);
  try {
    assert.match((await screen(env, a, 'trace')).body_html, /2 つ以上の公演で観た名前が、まだありません/);
    for (const [t, d, sid] of [['終わった舞台', '2026-08-05', '103'], ['舞台ひとつめ', '2026-11-02', '101']]) {
      const key = (await step(env, a, {post: '/api/add_work', body: {title: t, date: d}})).body.work_key;
      await step(env, a, {post: '/api/link_stage', body: {work_key: key, stage_id: sid}});
      await step(env, a, {post: '/api/rate', body: {work_key: key, verdict: '◎'}});
    }
    const pick = (await screen(env, a, 'trace')).body_html;
    assert.match(pick, /<h1>たどる ── 1 つの名前をたどる<\/h1>/);
    assert.match(pick, /<span class="pk-n">俳優甲<\/span><span class="pk-r">出演<\/span><span class="pk-c">2 作品<\/span>/);
    const thr = (await screen(env, a, 'trace', '?name=' + encodeURIComponent('俳優甲'))).body_html;
    assert.match(thr, /俳優甲 ── 2 作品/);
    assert.match(thr, /<div class="thr"><svg /);
  } finally { sqlite.close(); }
});

test('観劇史年表: the years of the works seen', async () => {
  const {env, sqlite} = withIndex();
  const a = await signIn(env);
  try {
    assert.match((await screen(env, a, 'chronicle')).body_html, /まだ年表を描けるだけの記録がありません/);
    for (const [t, d, v] of [['一の舞台', '2025-03-01', '◎'], ['二の舞台', '2026-02-01', '○'], ['三の舞台', '2026-05-01', '◎']]) {
      const key = (await step(env, a, {post: '/api/add_work', body: {title: t, date: d}})).body.work_key;
      await step(env, a, {post: '/api/rate', body: {work_key: key, verdict: v}});
    }
    const html = (await screen(env, a, 'chronicle')).body_html;
    assert.match(html, /<h1>観劇史年表 ── 何が始まった年か<\/h1>/);
    assert.match(html, /観劇の年表<\/span><span class="badge part">3 作品<\/span>/);
    assert.match(html, /<div class="chfig"><svg /);
    assert.match(html, /<b>2026<\/b><i>2 作品・のべ 2 回<\/i>/);
  } finally { sqlite.close(); }
});
