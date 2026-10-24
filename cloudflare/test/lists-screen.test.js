// 興味あり・お気に入り・購入済み on the Worker (screens/lists.js) and their writes.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {readFileSync} from 'node:fs';
import {setup, step, signIn} from './screens/harness.js';
import {wholeTour, pastShard} from '../src/screens/lists.js';

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
    // 見出し・説明・空のときの案内は起案者の指示 2026-10-18 の仕様変更（件数は見出しに入れない。空のときは絵の付いた案内）
    assert.match((await screen(env, a, 'interest')).body_html, /<h1>「興味あり」の公演<\/h1>[\s\S]*<section class="card tips eguide">[\s\S]*<a href="\/recommend\?t=__TAGURI_TOKEN__">おすすめ<\/a>」または「<a href="\/recommend\/reminder\?t=__TAGURI_TOKEN__">開幕リマインド<\/a>」、「<a href="\/search\?t=__TAGURI_TOKEN__">探す<\/a>」で「興味あり」と回答してください。[\s\S]*<svg class="tip-art"/);
    const fav = (await screen(env, a, 'favourites')).body_html;
    assert.match(fav, /<h1>お気に入り<\/h1>\n<p class="hsub">おすすめにかかわらず新着情報を知りたい題材や作り手がいるときは、お気に入りに追加することで情報の追跡ができます。<\/p>/);
    assert.match(fav, /<summary>[^]*要素を登録 <b>0件<\/b>/);
    assert.match(fav, /<p class="lead">表記ゆれ（漢字とカタカナ、送り仮名の違いなど）は、自動では見分けられない場合があります。<\/p>/);
    assert.doesNotMatch(fav, /観た記録に無い名前も登録できます|件を表示中/);
    assert.match(fav, /<details class="pbox" id="names" open>/);
    assert.match((await screen(env, a, 'tickets')).body_html, /<h1>購入済の公演<\/h1>[\s\S]*<section class="card tips eguide">[\s\S]*」で「購入済」と回答してください。<br>また「<a href="\/register\?t=__TAGURI_TOKEN__">観劇記録を追加<\/a>」で購入済の公演を追加してください。/);
  } finally { sqlite.close(); }
});

test('興味あり lists what was answered "interest", with the note; other users see nothing', async () => {
  const {env, sqlite} = withIndex();
  const a = await signIn(env), b = await signIn(env);
  try {
    assert.equal((await step(env, a, {post: '/api/react', body: {stage_id: '101', value: 'interest', nofill: true}})).status, 200);
    assert.equal((await step(env, a, {post: '/api/react', body: {stage_id: '101', note: '俳優甲 & 乙'}})).status, 200);
    const html = (await screen(env, a, 'interest')).body_html;
    assert.match(html, /<h1>「興味あり」の公演<\/h1>/);   // 見出しに件数は入れない（起案者の指示 2026-10-18）
    assert.equal((html.match(/<article class="ticket interest"/g) || []).length, 1);
    assert.match(html, /<article class="ticket interest" data-stage="101"/);
    assert.match(html, /<span class="wnt">俳優甲 &amp; 乙<\/span>/);
    // 興味ありの一覧は 興味なし・購入済・行けない を畳まずに（起案者 2026-10-17）。2026-10-19 からは、押してある「興味あり」も印付きで出す（押し直しで解除）
    assert.match(html, /<span class="btns" data-stage="101" data-current="interest"><button data-v="interest" aria-pressed="true" class="picked">興味あり<\/button><button data-v="nointerest">興味なし<\/button><button data-v="owned">購入済<\/button><span class="said">/);
    assert.match(html, /<nav class="idx" aria-label="月で切り替える">/);
    assert.match((await screen(env, b, 'interest')).body_html, /「興味あり」の公演はまだありません/);
    // Not interested: out of 興味あり.
    await step(env, a, {post: '/api/react', body: {stage_id: '101', value: 'nointerest', nofill: true}});
    assert.match((await screen(env, a, 'interest')).body_html, /「興味あり」の公演はまだありません/);
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
    // 見出しは「お気に入り」だけ。件数は表示中の 1 行で。並べ替えは月のタブより下。並び方の説明の段落と
    // 「すべてを表示しています」の 1 行は出さない（起案者の指示 2026-10-18 の仕様変更）
    assert.match(fav, /<h1>お気に入り(?:<button[^>]*share-page-btn[\s\S]*?<\/button>)?<\/h1>/);
    assert.match(fav, /全 1 件中 1 件を表示中/);
    assert.match(fav, /<nav class="idx" aria-label="月で切り替える">[\s\S]*<form class="sortf"[\s\S]*<div class="tickets">/);
    assert.doesNotMatch(fav, /すべてを表示しています|に並んでいます。順位は付けていません。観ると決めたら/);
    assert.match(fav, /<article class="ticket favourite" data-stage="101"/);
    // 場所はこのページだけの絞り込み（保存しない）。当たらない県では 0 件と、全国に戻す案内
    const pin = /<span class="pl">([^<]+)<\/span><span class="pn">1件<\/span>/.exec(fav);
    assert.ok(pin, 'the stage counts under its prefecture');
    const here = (await screen(env, a, 'favourites', '?f=1&pref=' + encodeURIComponent(pin[1]))).body_html;
    assert.match(here, /<article class="ticket favourite" data-stage="101"/);
    const far = pin[1] === '沖縄県' ? '北海道' : '沖縄県';
    const none = (await screen(env, a, 'favourites', '?f=1&pref=' + encodeURIComponent(far))).body_html;
    assert.doesNotMatch(none, /data-stage="101"/);
    assert.match(none, new RegExp(`<b>${far}</b>で観られるお気に入りの公演はありません（全国では 1 件）`));
    assert.match((await screen(env, a, 'favourites')).body_html, /data-stage="101"/);
    // 理由の欄は出さず、当たった名前をハッシュタグで並べる（起案者 2026-10-15）
    assert.match(fav, /<div class="favtags"><a class="ftag" href="\/recommend\/favourites\?t=__TAGURI_TOKEN__&amp;n=%E4%BF%B3%E5%84%AA%E7%94%B2">#俳優甲<\/a><\/div>/);
    assert.doesNotMatch(fav, /なぜお知らせしているか/);
    // 登録した名前も、カードのハッシュタグと同じ形（起案者 2026-10-17）。札は「#人「俳優甲」」の形（起案者の指示 2026-10-18）
    assert.match(fav, /<span class="tag ftag" data-kind="人" data-name="俳優甲"><a class="tgn" href="\/recommend\/favourites\?t=__TAGURI_TOKEN__&amp;n=%E4%BF%B3%E5%84%AA%E7%94%B2">#人「俳優甲」<\/a><button data-fav="remove" aria-label="「俳優甲」を外す">✕<\/button><\/span>/);
    assert.doesNotMatch(fav, /data-v="interest"/);                 // no 興味あり here, only 購入済み
    assert.match(fav, /<span class="btns" data-stage="101"><button data-v="owned">購入済みにする<\/button>/);
    // Group names match the producing company only.
    await step(env, a, {post: '/api/favourite', body: {action: 'add', kind: '団体', name: '劇団乙'}});
    assert.match((await screen(env, a, 'favourites')).body_html, /全 2 件中 2 件を表示中[\s\S]*data-stage="102"/);
    await step(env, a, {post: '/api/favourite', body: {action: 'remove', kind: '団体', name: '劇団乙'}});
    assert.match((await screen(env, a, 'favourites')).body_html, /全 1 件中 1 件を表示中/);
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
    // 出さない語 is set on おすすめ only; お気に入り shows 登録した名前 (選び方) and 場所 (表示の絞り込み).
    const favHtml = (await screen(env, a, 'favourites')).body_html;
    assert.doesNotMatch(favHtml, /id="declined"/);
    assert.match(favHtml, /<div class="fil2 tune"><details class="pbox" id="names"[\s\S]*<div class="fil2 narrow"><form class="pfil" method="get" action="\/recommend\/favourites">/);
    assert.match((await screen(env, a, 'recommend')).body_html, /使わない言葉 <b>1語<\/b>[\s\S]*「バレエ」/);
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
    assert.match(html, /<h1>購入済の公演<\/h1>/);   // 見出しに件数は入れない（起案者の指示 2026-10-18）
    assert.equal((html.match(/<article class="ticket owned"/g) || []).length, 1);
    assert.match(html, /<article class="ticket owned" data-stage="101"/);
    assert.match(html, /<span class="mt-row">2026\.11\.03\(火\) 14:00 <button data-mt-del="101" data-date="2026-11-03" data-time="14:00">取り消す<\/button><\/span>/);
    assert.match(html, /min="2026-11-01" max="2026-11-10"/);
    assert.doesNotMatch((await screen(env, a, 'interest')).body_html, /data-stage="101"/);
    // A memo before seeing it, only on owned stages; it goes with the work once seen.
    assert.match(html, /<details class="nn pre" data-stage="101"><summary>観る前のメモを書く/);
    await step(env, a, {post: '/api/react', body: {stage_id: '101', note_pre: '原作を読んで楽しみ'}});
    assert.match((await screen(env, a, 'tickets')).body_html, /観る前のメモ<span class="nnv">原作を読んで楽しみ<\/span>/);
    assert.doesNotMatch((await screen(env, a, 'recommend')).body_html, /data-prenote/);
    // After the ticket's date the stage leaves 購入済み and waits for a rating.
    env.CLOCK = {today: '2026-11-04', now: Date.parse('2026-11-04T03:00:00Z')};
    assert.match((await screen(env, a, 'tickets')).body_html, /購入済の公演はまだありません/);
    assert.match((await screen(env, a, 'unrated')).body_html, /舞台ひとつめ/);
    assert.equal(sqlite.prepare("SELECT count(*) AS n FROM works WHERE stage_id='101'").get().n, 1);
    assert.equal(sqlite.prepare("SELECT note_motive FROM works WHERE stage_id='101'").get().note_motive, '原作を読んで楽しみ');
    await screen(env, a, 'tickets');
    assert.equal(sqlite.prepare("SELECT count(*) AS n FROM works WHERE stage_id='101'").get().n, 1);
  } finally { sqlite.close(); }
});

test('開幕リマインド: every stage opening this week, with a prefecture filter of its own page', async () => {
  const {env, sqlite} = withIndex();
  const a = await signIn(env);
  try {
    env.CLOCK = {today: '2026-10-20', now: Date.parse('2026-10-20T03:00:00Z')};
    const html = (await screen(env, a, 'reminder')).body_html;
    // 見出し・前置きの 1 文・件数の 1 行の位置（週のタブの下）、「直近の観劇予定」の枠を外したことは
    // 起案者の指示 2026-10-18 の仕様変更
    assert.match(html, /<h1>開幕リマインド<\/h1>\n<p class="hsub">開幕リマインドでは、おすすめやお気に入りにかかわらず、今週・来週開幕予定の公演を全件掲載しています。<\/p>/);
    assert.match(html, /<nav class="idx" aria-label="週で切り替える">[\s\S]*<\/nav>\n<p class="rcount"><b>全国<\/b>／今週開幕する公演 0 件を表示中<\/p>\n<section class="dgcard dgmain">/);
    assert.doesNotMatch(html, /直近の観劇予定|見逃していませんか|好みに関係なく/);
    assert.match(html, /今週<span class="mn">0<\/span>/);
    assert.match(html, /来週<span class="mn">1<\/span>/);
    const next = (await screen(env, a, 'reminder', '?w=next')).body_html;
    assert.match(next, /<li class="dgli dgfold und" data-stage="101"><details class="dgopen"><summary>/);
    assert.match(next, /<input type="hidden" name="w" value="next">/);
    await step(env, a, {post: '/api/react', body: {stage_id: '101', value: 'interest', nofill: true}});
    const answered = (await screen(env, a, 'reminder', '?w=next')).body_html;
    assert.match(answered, /<li class="dgli dgfold trk" data-stage="101">/);
    // 答えた公演は「回答を直す」1 つ（押すと三択が開く）。
    assert.match(answered, /<button class="wnb" data-btns-open="1">回答を直す<\/button><span class="btns" hidden data-stage="101" data-current="interest">/);
    // The filter chosen here stays on this page only (起案者の指示 2026-10-17): the week tabs carry it,
    // おすすめ and the next visit use the 設定 default.
    const osaka = (await screen(env, a, 'reminder', '?w=next&f=1&pref=' + encodeURIComponent('大阪府'))).body_html;
    assert.match(osaka, /いまは<b>大阪府（1 県）<\/b>/);
    assert.match(osaka, /href="\/recommend\/reminder\?t=__TAGURI_TOKEN__&w=this&amp;f=1&amp;pref=%E5%A4%A7%E9%98%AA%E5%BA%9C"/);
    assert.match((await screen(env, a, 'recommend')).body_html, /いまは<b>全国<\/b>/);
    assert.match((await screen(env, a, 'reminder', '?w=next')).body_html, /いまは<b>全国<\/b>/);
    await step(env, a, {post: '/api/pref_setting', body: {prefs: ['大阪府']}});
    assert.match((await screen(env, a, 'reminder', '?w=next')).body_html, /いまは<b>大阪府（1 県）<\/b>/);
    assert.match((await screen(env, a, 'reminder', '?w=next&f=1')).body_html, /いまは<b>全国<\/b>/);
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
    // 開いたときの中身は、開いたときに読む（/api/reminder_detail）。画面には読む先の印だけを置く
    assert.match(html, /data-stage="777"><details class="dgopen"><summary>[\s\S]*?<\/summary><div class="dgdetail"><div class="dginfo"><div class="dglazy" data-detail="777"><\/div>/);
    assert.doesNotMatch(html, /海辺の町の三姉妹の話。/);
    const det = (await step(env, a, {get: '/api/reminder_detail?sids=777,bad%20id'})).body;
    assert.deepEqual(Object.keys(det.html), ['777']);
    assert.match(det.html['777'], /山田太郎、鈴木花子[\s\S]*?海辺の町の三姉妹の話。/);
    assert.equal((await step(env, '', {get: '/api/reminder_detail?sids=777'})).status, 401);
    await step(env, a, {post: '/api/react', body: {stage_id: '777', value: 'interest', nofill: true}});
    assert.match((await screen(env, a, 'reminder')).body_html, /<li class="dgli dgfold trk" data-stage="777">/);
    const it = (await screen(env, a, 'interest')).body_html;
    assert.match(it, /<h1>「興味あり」の公演<\/h1>/);   // 見出しに件数は入れない（起案者の指示 2026-10-18）
    assert.equal((it.match(/<article class="ticket interest"/g) || []).length, 1);
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
    assert.match(reg, /<h1>観劇記録を追加<\/h1>/);
    assert.match(reg, /<span class="badge part">2 件<\/span>/);
    // 行けばよかった（2026-10-20 に「観ればよかった」から名前を変え、題名 1 行・くわしくは畳む形にした）
    assert.match(reg, /<summary><h2[^>]*>[\s\S]*?行けばよかった/);
    assert.match(reg, /<b class="mt">舞台ひとつめ<\/b>[\s\S]*<summary>くわしく<\/summary>[\s\S]*<span class="cl">出演<\/span><span class="cv">俳優甲、俳優乙<\/span>/);
    assert.match(reg, /<b class="mt">聞いたことのない舞台<\/b>/);
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
    assert.match(empty, /今後の公演 3 件と観た記録の両方から探します/);
    // A new account (no records yet) still gets the month calendar, opened on the coming stages
    // (2026-10-14 起案者「『探す』にあったカレンダーが消えてる」).
    assert.match(empty, /<div class="cal" id="cal">/);
    assert.match(empty, /aria-current="page"[^>]*>今後の公演|今後の公演[^<]*<span class="mn">3<\/span>/);
    assert.match(empty, /class="cal-c l\d/);
    // A coming stage found by a cast name: the card with 「ヒットした箇所」 on top.
    const byName = (await screen(env, a, 'search', '?q=' + encodeURIComponent('俳優甲'))).body_html;
    assert.match(byName, /<h2>今後の公演 1 件<\/h2>/);
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
    assert.match((await screen(env, a, 'search', '?q=' + encodeURIComponent('存在しない公演'))).body_html, /依頼を控えました。<b>ただ、依頼された題名を毎日の更新で探す段はまだ準備中で、まだ探していません。<\/b>/);
    assert.equal((await step(env, a, {post: '/api/search_request', body: {q: 'x'}})).status, 400);
  } finally { sqlite.close(); }
});

// 「たどる」の画面は外し、糸の図だけを人物のページに載せる（起案者の指示 2026-10-19「名前の一覧もネットワーク図もいらない。
// 糸で繋がってる図だけ各人物の個人ページに入れてくれればok」）
test('人物のページ: a name seen in two rated stages gets the thread; the 「たどる」 screen is gone', async () => {
  const {env, sqlite} = withIndex();
  const a = await signIn(env);
  const person = () => step(env, a, {get: '/api/screen/person?n=' + encodeURIComponent('俳優甲') + '&r=' + encodeURIComponent('出演')}).then(r => r.body.body_html);
  try {
    assert.doesNotMatch(await person(), /観た公演をつなぐ糸/);
    for (const [t, d, sid] of [['終わった舞台', '2026-08-05', '103'], ['舞台ひとつめ', '2026-11-02', '101']]) {
      const key = (await step(env, a, {post: '/api/add_work', body: {title: t, date: d}})).body.work_key;
      await step(env, a, {post: '/api/link_stage', body: {work_key: key, stage_id: sid}});
      await step(env, a, {post: '/api/rate', body: {work_key: key, verdict: '◎'}});
    }
    const html = await person();
    assert.match(html, /観た公演をつなぐ糸 ── 2 作品/);
    assert.match(html, /<div class="thr"><svg /);
    assert.doesNotMatch(html, /records\/trace/);
    assert.equal((await step(env, a, {get: '/api/screen/trace'})).status, 404);
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
    assert.match(html, /<h1>観劇史年表 ── 何が始まった年か(?:<button[^>]*share-page-btn[\s\S]*?<\/button>)?<\/h1>/);
    assert.match(html, /観劇の年表<\/span><span class="badge part">3 作品<\/span>/);
    assert.match(html, /<div class="chfig"><svg /);
    assert.match(html, /<b>2026<\/b><i>2 作品・のべ 2 回<\/i>/);
  } finally { sqlite.close(); }
});

// 2026-10-14 起案者「購入済みに作品が入っているのに、公演カレンダーになにも表示されない」: a stage the user
// owns that the (stale) index lacks is taken from the catalogue, as 購入済み公演 does.
test('公演カレンダー shows an owned stage that only the catalogue has', async () => {
  const {env, sqlite} = withIndex();
  const a = await signIn(env);
  try {
    env.CLOCK = {today: '2026-10-20', now: Date.parse('2026-10-20T03:00:00Z')};
    sqlite.prepare("INSERT INTO catalogue(id,title,date,venue,url,metadata) VALUES('778','一覧だけの舞台','2026-10-25','劇場Y','',?)")
      .run(JSON.stringify({end_date: '2026-11-03'}));
    assert.equal((await step(env, a, {post: '/api/react', body: {stage_id: '778', value: 'owned', nofill: true}})).status, 200);
    const owned = (await screen(env, a, 'tickets')).body_html;
    assert.match(owned, /一覧だけの舞台/);
    assert.match(owned, /data-btns-open="1">回答を直す<\/button><span class="btns" hidden data-stage="778" data-current="owned">/);
    assert.match((await screen(env, a, 'calendar')).body_html, /一覧だけの舞台/);
    // 2026-10-15 起案者「場所絞ったら公演カレンダー0件になる」: the catalogue has no prefecture, so a
    // place filter cannot show it; the calendar says how many it left out instead of a silent 0.
    const tokyo = (await screen(env, a, 'calendar', '?pref=' + encodeURIComponent('東京都'))).body_html;
    assert.match(tokyo, /都道府県が分からない公演が 1 件あり、場所で絞ると表示できません/);
    // 開幕リマインド keeps them, below the chosen prefecture's list (it is there so nothing opens unnoticed).
    const rem = (await screen(env, a, 'reminder', '?f=1&pref=' + encodeURIComponent('東京都'))).body_html;
    // 「直近の観劇予定」の枠を外したので（起案者の指示 2026-10-18）、開幕する公演の枠の最後に入る
    assert.match(rem, /<summary>都道府県が分からない公演　1 件<\/summary>[\s\S]*一覧だけの舞台[\s\S]*<\/details><\/section>\n*$/);
  } finally { sqlite.close(); }
});

// 2026-10-15 起案者「都道府県がわからない作品しかない」: the catalogue has no prefecture, venue_pref
// (migration 0024, delivered by deliver_catalogue.py) gives it by venue, so the place filters keep the stage.
test('a catalogue stage takes its prefecture from venue_pref', async () => {
  const {env, sqlite} = withIndex();
  const a = await signIn(env);
  try {
    env.CLOCK = {today: '2026-10-20', now: Date.parse('2026-10-20T03:00:00Z')};
    sqlite.prepare("INSERT INTO catalogue(id,title,date,venue,url,metadata) VALUES('779','劇場の分かる舞台','2026-10-25','劇場Z','',?)")
      .run(JSON.stringify({end_date: '2026-11-03'}));
    sqlite.prepare("INSERT INTO venue_pref(venue,pref) VALUES('劇場Z','大阪府')").run();
    await step(env, a, {post: '/api/react', body: {stage_id: '779', value: 'owned', nofill: true}});
    const cal = (await screen(env, a, 'calendar', '?pref=' + encodeURIComponent('大阪府'))).body_html;
    assert.match(cal, /劇場の分かる舞台/);
    assert.doesNotMatch(cal, /都道府県が分からない公演/);
    const rem = (await screen(env, a, 'reminder', '?f=1&pref=' + encodeURIComponent('大阪府'))).body_html;
    assert.match(rem, /<b>大阪府<\/b>で [^<]*に開幕する公演 ︰ <b>1 件<\/b>/);   // 文の形は起案者の指示 2026-10-18
    assert.doesNotMatch(rem, /都道府県が分からない公演/);
  } finally { sqlite.close(); }
});

// 2026-10-14 起案者「たぐりが集めている公演から出してよ勿論」: a name added to お気に入り is
// looked up in the whole delivered catalogue too, not only in the stages with a card.
test('お気に入り finds a registered name in the catalogue at once, also without a card', async () => {
  const {env, sqlite} = withIndex();
  const a = await signIn(env);
  try {
    env.CLOCK = {today: '2026-10-20', now: Date.parse('2026-10-20T03:00:00Z')};
    sqlite.prepare("INSERT INTO catalogue(id,title,date,venue,url,metadata) VALUES('888','カードの無い新作','2026-11-05','劇場Y','',?)")
      .run(JSON.stringify({end_date: '2026-11-12', group: '劇団 Y', fields: {出演: '山田 花子、佐藤一郎'}, synopsis: '港町の話。'}));
    sqlite.prepare("INSERT INTO catalogue(id,title,date,venue,url,metadata) VALUES('889','終わった公演','2026-05-01','劇場Y','',?)")
      .run(JSON.stringify({end_date: '2026-05-03', fields: {出演: '山田花子'}}));
    await step(env, a, {post: '/api/favourite', body: {action: 'add', kind: '人', name: '山田花子'}});
    await step(env, a, {post: '/api/favourite', body: {action: 'add', kind: '団体', name: '劇団Y'}});
    const html = (await screen(env, a, 'favourites')).body_html;
    assert.match(html, /<article class="ticket favourite" data-stage="888"[\s\S]*?カードの無い新作/);
    assert.match(html, /class="ftag"[^>]*>#山田花子<\/a>/);
    assert.match(html, /class="ftag"[^>]*>#劇団Y<\/a>/);
    assert.doesNotMatch(html, /終わった公演/);
  } finally { sqlite.close(); }
});

test('購入済みにする on お気に入り adds the stage to 購入済み公演 and keeps it on お気に入り (起案者 2026-10-15)', async () => {
  const {env, sqlite} = withIndex();
  const a = await signIn(env);
  try {
    await step(env, a, {post: '/api/favourite', body: {action: 'add', kind: '人', name: '俳優甲'}});
    assert.match((await screen(env, a, 'favourites')).body_html, /全 1 件中 1 件を表示中/);
    assert.equal((await step(env, a, {post: '/api/react', body: {stage_id: '101', value: 'owned', nofill: true}})).status, 200);
    // お気に入りには残し、ボタンの代わりに「購入済み」の印を出す（起案者 2026-10-15「購入済み押してもお気に入りから消さないで」）
    const fav = (await screen(env, a, 'favourites')).body_html;
    assert.match(fav, /全 1 件中 1 件を表示中/);
    assert.match(fav, /<article class="ticket favourite" data-stage="101"[\s\S]*<span class="owned-mark">購入済み/);
    // 2026-10-19: 購入済のボタンは印付きで残し、押し直しで解除できる
    assert.match(fav, /<button data-v="owned" aria-pressed="true" class="picked">購入済<\/button>/);
    const t = (await screen(env, a, 'tickets')).body_html;
    assert.match(t, /<h1>購入済の公演<\/h1>/);   // 見出しに件数は入れない（起案者の指示 2026-10-18）
    assert.equal((t.match(/<article class="ticket owned"/g) || []).length, 1);
    assert.match(t, /<article class="ticket owned" data-stage="101"/);
  } finally { sqlite.close(); }
});

test('人 matches the whole name: 上村聡 does not pick up 上村聡史 (起案者 2026-10-15)', async () => {
  const {env, sqlite} = withIndex();
  const a = await signIn(env);
  try {
    const add = (id, title, cast) => sqlite.prepare("INSERT INTO catalogue(id,title,date,venue,url,metadata) VALUES(?,?,'2026-10-20','劇場Q','',?)")
      .run(id, title, JSON.stringify({end_date: '2026-10-25', fields: {'出演': cast, '演出': '演出家丙'}}));
    add('961', '聡の舞台', '上村 聡、俳優乙');
    add('962', '聡史の舞台', '俳優乙');
    sqlite.prepare("UPDATE catalogue SET metadata=? WHERE id='962'").run(JSON.stringify({end_date: '2026-10-25', fields: {'出演': '俳優乙', '演出': '上村聡史'}}));
    await step(env, a, {post: '/api/favourite', body: {action: 'add', kind: '人', name: '上村聡'}});
    const fav = (await screen(env, a, 'favourites')).body_html;
    assert.match(fav, /data-stage="961"/);
    assert.doesNotMatch(fav, /data-stage="962"/);
    assert.match(fav, /全 1 件中 1 件を表示中/);
    // 名前全体なら当たる
    await step(env, a, {post: '/api/favourite', body: {action: 'add', kind: '人', name: '上村聡史'}});
    assert.match((await screen(env, a, 'favourites')).body_html, /全 2 件中 2 件を表示中[\s\S]*data-stage="962"/);
  } finally { sqlite.close(); }
});

test('興味あり added from 開幕リマインド says so in place of おすすめ理由, and a note keeps it (起案者 2026-10-15)', async () => {
  const {env, sqlite} = withIndex();
  const a = await signIn(env);
  try {
    await step(env, a, {post: '/api/react', body: {stage_id: '101', value: 'interest', nofill: true, from: 'reminder'}});
    await step(env, a, {post: '/api/react', body: {stage_id: '102', value: 'interest', nofill: true}});
    // 理由を書いても、足した場所は変わらない
    await step(env, a, {post: '/api/react', body: {stage_id: '101', note: 'ポスターがかわいい'}});
    const html = (await screen(env, a, 'interest')).body_html;
    const card = id => html.slice(html.indexOf(`data-stage="${id}"`), html.indexOf('</article>', html.indexOf(`data-stage="${id}"`)));
    assert.match(card('101'), /<div class="whyh origin">[\s\S]*開幕リマインドからの追加<\/div>/);
    assert.doesNotMatch(card('101'), /おすすめ理由|<ul class="why">/);
    assert.match(card('101'), /<span class="wnt">ポスターがかわいい<\/span>/);
    // 書いた理由は、ふだんは畳む（「なぜ気になったか」で開く。起案者 2026-10-15・17）
    assert.match(card('101'), /<details class="wnw why-memo"><summary>/);
    assert.match(card('102'), /おすすめ理由/);
    assert.equal(sqlite.prepare("SELECT source FROM reaction WHERE stage_id='101' AND interest=1").get().source, 'reminder');
  } finally { sqlite.close(); }
});

test('migration 0025 relabels the older 興味あり as added from 開幕リマインド (起案者 2026-10-15)', async () => {
  const {env, sqlite} = withIndex();
  const a = await signIn(env);
  try {
    const uid = sqlite.prepare('SELECT id FROM users').get().id;
    const put = (sid, interest, source, at) => sqlite.prepare('INSERT INTO reaction(user_id,label,stage_id,interest,source,updated_at) VALUES(?,?,?,?,?,?)')
      .run(uid, '2026-10-14', sid, interest, source, at);
    put('101', 1, 'screen', '2026-10-14T10:00:00.000Z');
    put('102', 1, 'screen_tour', '2026-10-14T10:00:00.000Z');
    put('103', 0, 'screen', '2026-10-14T10:00:00.000Z');          // 興味なしは触らない
    put('104', 1, 'screen', '2026-10-15T23:50:00.000Z');          // PR #28 より後の 'screen' はおすすめから押したもの。触らない
    put('105', 1, 'screen', '2026-10-15T23:00:00.000Z');          // 理由を書いて時刻が新しくなった古い行
    sqlite.exec(readFileSync(new URL('../migrations/0025.sql', import.meta.url), 'utf8'));
    const src = Object.fromEntries(sqlite.prepare('SELECT stage_id,source FROM reaction').all().map(r => [r.stage_id, r.source]));
    assert.deepEqual(src, {101: 'reminder', 102: 'reminder_tour', 103: 'screen', 104: 'screen', 105: 'reminder'});
    assert.match((await screen(env, a, 'interest')).body_html, /data-stage="101"[\s\S]*?開幕リマインドからの追加/);
  } finally { sqlite.close(); }
});

test('並べ替え: 興味あり・お気に入り・購入済み公演 can be sorted; 上演日の近い順 by default (起案者 2026-10-15)', async () => {
  const {env, sqlite} = withIndex();
  const a = await signIn(env);
  try {
    const add = (id, title, start, end, venue) => sqlite.prepare("INSERT INTO catalogue(id,title,date,venue,url,metadata) VALUES(?,?,?,?,'',?)")
      .run(id, title, start, venue, JSON.stringify({end_date: end}));
    add('971', 'う', '2026-10-20', '2026-12-01', '劇場Q');
    add('972', 'あ', '2026-10-25', '2026-10-27', '劇場Q');
    add('973', 'い', '2026-10-18', '2026-11-05', '劇場Q');
    for (const sid of ['972', '973', '971']) await step(env, a, {post: '/api/react', body: {stage_id: sid, value: 'interest', nofill: true}});
    // 押した時刻（テストの時計は止まっているので、ここで付ける）: 972 → 973 → 971 の順に押した
    [['972', '10:00'], ['973', '11:00'], ['971', '12:00']].forEach(([sid, t]) =>
      sqlite.prepare('UPDATE reaction SET updated_at=? WHERE stage_id=?').run(`2026-10-12T${t}:00.000Z`, sid));
    const order = async q => {
      const html = (await screen(env, a, 'interest', q)).body_html;
      return [...html.matchAll(/<article class="ticket interest" data-stage="(97\d)"/g)].map(m => m[1]);
    };
    const def = (await screen(env, a, 'interest')).body_html;
    assert.match(def, /<select name="s"[^>]*><option value="start" selected>上演日の近い順<\/option>/);
    assert.deepEqual(await order(''), ['973', '971', '972']);           // 開幕 10/18, 10/20, 10/25
    assert.deepEqual(await order('?s=end'), ['972', '973', '971']);     // 楽日 10/27, 11/5, 12/1
    assert.deepEqual(await order('?s=title'), ['972', '973', '971']);   // あ・い・う
    assert.deepEqual(await order('?s=added'), ['971', '973', '972']);   // 押したのが新しい順
    assert.deepEqual(await order('?s=bogus'), ['973', '971', '972']);
    assert.match((await screen(env, a, 'interest', '?s=end')).body_html, /<b>楽日の近い順<\/b>に並んでいます/);
    for (const sid of ['971', '972']) await step(env, a, {post: '/api/react', body: {stage_id: sid, value: 'owned', nofill: true}});
    const t = (await screen(env, a, 'tickets', '?s=end')).body_html;
    assert.match(t, /<option value="end" selected>楽日の近い順/);
    assert.ok(t.indexOf('data-stage="972"') < t.indexOf('data-stage="971"'));
  } finally { sqlite.close(); }
});

test('お気に入りのハッシュタグ: the name coming stages, works seen and (on request) past stages (起案者 2026-10-15)', async () => {
  const {env, sqlite} = withIndex();
  const a = await signIn(env);
  try {
    await step(env, a, {post: '/api/favourite', body: {action: 'add', kind: '人', name: '俳優甲'}});
    // 観た公演（103 は索引で 俳優甲 が出ている。終わった舞台）
    const key = (await step(env, a, {post: '/api/add_work', body: {title: '終わった舞台', date: '2026-08-05'}})).body.work_key;
    await step(env, a, {post: '/api/link_stage', body: {work_key: key, stage_id: '103'}});
    await step(env, a, {post: '/api/rate', body: {work_key: key, verdict: '5/5'}});
    // 過去の公演の一覧: 当たるもの・名前の一部だけ当たるもの
    const put = (id, title, people) => sqlite.prepare("INSERT INTO past_stage(stage_id,title,tkey,start,end,venue,grp,pref,people) VALUES(?,?,?,?,?,'劇場P','劇団P','東京都',?)")
      .run(id, title, title, '2023-05-01', '2023-05-10', JSON.stringify(people));
    put('p1', '昔の舞台', [['出演', '俳優甲']]);
    put('p2', '別人の舞台', [['出演', '俳優甲乙']]);
    const v = (await screen(env, a, 'favourites', '?n=' + encodeURIComponent('俳優甲'))).body_html;
    assert.match(v, /<h1><span class="ftag big">#俳優甲<\/span> の公演<\/h1>/);
    assert.match(v, /今後の公演 <span class="cnt">1 件<\/span>[\s\S]*data-stage="101"/);
    assert.match(v, /観た公演 <span class="cnt">1 件<\/span>[\s\S]*終わった舞台[\s\S]*★5/);
    // 過去の公演は開いたときに自動で出す（起案者 2026-10-15）。名前全体で当てる
    assert.match(v, /2023\/05\/01〜05\/10<\/span><span class="t">昔の舞台/);
    assert.doesNotMatch(v, /別人の舞台/);
    // ツアー（同じ題名・団体の別会場）は 1 行にまとめる
    sqlite.prepare("INSERT INTO past_stage(stage_id,title,tkey,start,end,venue,grp,pref,people) VALUES('p3','昔の舞台','昔の舞台','2023-06-01','2023-06-03','劇場R','劇団P','大阪府',?)").run(JSON.stringify([['出演', '俳優甲']]));
    const t = (await screen(env, a, 'favourites', '?n=' + encodeURIComponent('俳優甲'))).body_html;
    assert.match(t, /2023\/05\/01〜06\/03<\/span><span class="t">昔の舞台<\/span><span class="w">劇団P／劇場P ほか 1 会場<\/span>/);
    assert.equal((t.match(/昔の舞台/g) || []).length, 1);
    // 1 日の回数の上限を越えたら探さない
    sqlite.prepare("INSERT INTO rec_meta(k,v) VALUES('past_scan',?) ON CONFLICT(k) DO UPDATE SET v=excluded.v").run('2026-10-12 150');
    assert.match((await screen(env, a, 'favourites', '?n=' + encodeURIComponent('俳優甲'))).body_html, /代わりの検索も今日の回数の上限に達しました/);
  } finally { sqlite.close(); }
});

test('wholeTour: a tour card shows the whole run, without the per-region schedule (起案者 2026-10-15)', async () => {
  const {env, sqlite} = withIndex();
  try {
    const add = (id, start, end, venue) => sqlite.prepare("INSERT INTO catalogue(id,title,date,venue,url,metadata) VALUES(?,'ツアーの舞台',?,?,'',?)")
      .run(id, start, venue, JSON.stringify({end_date: end}));
    add('981', '2026-10-06', '2026-10-25', '劇場T');
    add('982', '2026-11-07', '2026-11-10', '劇場O');
    const card = '<article class="ticket favourite" data-stage="981" data-tours="982"><div class="stub"><span class="sd" data-range="10/6〜10/25" data-state="上演中" data-tour="東京公演／劇場T"><b>10/6</b></span></div>'
      + '<div class="tourfull"><div class="tf-row here"><span class="tf-loc">東京公演</span></div><div class="tf-row"><span class="tf-loc">大阪公演</span></div></div><div class="cast">出演</div></article>';
    const [out] = await wholeTour({db: env.DB, today: '2026-10-12'}, [card], [{stage_id: '981', sids: ['981', '982']}]);
    assert.match(out, /data-range="10\/6〜11\/10" data-state="上演中"/);
    assert.doesNotMatch(out, /data-tour=|tourfull|大阪公演/);
    assert.match(out, /<div class="cast">出演<\/div>/);
  } finally { sqlite.close(); }
});

test('過去の公演は名前の索引（R2）から読み、D1 の一覧は読まない (起案者 2026-10-15「すぐ表示できるための方法」)', async () => {
  const {env, sqlite} = withIndex();
  const a = await signIn(env);
  try {
    assert.equal(pastShard('上村聡'), 0x9b);                             // deliver_past_index.shard_of と同じ
    const shard = {v: 1, stages: {s1: ['索引の舞台', '索引の舞台', '2024-03-01', '2024-03-10', '本多劇場', '劇団あおば'],
      s2: ['索引の舞台', '索引の舞台', '2024-04-01', '2024-04-03', '梅田劇場', '劇団あおば']}, names: {'上村聡': ['s1', 's2']}};
    const gets = [];
    env.POSTERS = {get: async key => { gets.push(key); return key === 'pastidx/v1/9b.json' ? {json: async () => shard} : null; }};
    // D1 の一覧には別の行（索引を読めば使われない）
    sqlite.prepare("INSERT INTO past_stage(stage_id,title,tkey,start,end,venue,grp,pref,people) VALUES('d1','一覧だけの舞台','x','2023-01-01','2023-01-02','劇場','劇団','東京都',?)").run(JSON.stringify([['出演', '上村聡']]));
    const v = (await screen(env, a, 'favourites', '?n=' + encodeURIComponent('上村 聡'))).body_html;
    assert.deepEqual(gets, ['pastidx/v1/9b.json']);
    assert.match(v, /2024\/03\/01〜04\/03<\/span><span class="t">索引の舞台<\/span><span class="w">劇団あおば／本多劇場 ほか 1 会場<\/span>/);
    assert.doesNotMatch(v, /一覧だけの舞台/);
    assert.equal(sqlite.prepare("SELECT v FROM rec_meta WHERE k='past_scan'").get(), undefined);   // 一覧を読む回数を使っていない
    // 索引がまだ無いときは、一覧を読む（回数に上限あり）
    env.POSTERS = {get: async () => null};
    assert.match((await screen(env, a, 'favourites', '?n=' + encodeURIComponent('上村聡'))).body_html, /一覧だけの舞台/);
  } finally { sqlite.close(); }
});

test('行く日が過ぎた券は、その回の記録（未評価）になる。千穐楽を待たない・二重に作らない・消した回は作り直さない', async () => {
  const {env, sqlite} = withIndex();
  const a = await signIn(env);
  const works = () => sqlite.prepare("SELECT work_key,first_date,time,verdict,note_motive FROM works WHERE stage_id='101' ORDER BY work_key").all();
  try {
    await step(env, a, {post: '/api/react', body: {stage_id: '101', value: 'owned', nofill: true}});
    await step(env, a, {post: '/api/react', body: {stage_id: '101', note_pre: '楽しみ'}});
    for (const t of [{date: '2026-11-03', time: '14:00'}, {date: '2026-11-03', time: '18:00'}, {date: '2026-11-05'}])
      assert.equal((await step(env, a, {post: '/api/ticket', body: {stage_id: '101', ...t}})).status, 200);
    // 11/3 の 17:00（日本時間）: 昼の回だけ過ぎた。会期（〜11/10）の途中でも未評価に出る
    env.CLOCK = {today: '2026-11-03', now: Date.parse('2026-11-03T08:00:00Z')};
    assert.match((await screen(env, a, 'unrated')).body_html, /舞台ひとつめ/);
    assert.deepEqual(works().map(w => [w.first_date, w.time, w.verdict, w.note_motive]), [['2026-11-03', '14:00', null, '楽しみ']]);
    // 翌日: 夜の回も別の記録に。何度開いても増えない。11/5 はまだ
    env.CLOCK = {today: '2026-11-04', now: Date.parse('2026-11-04T03:00:00Z')};
    await screen(env, a, 'unrated');
    await screen(env, a, 'unrated');
    assert.deepEqual(works().map(w => [w.first_date, w.time]), [['2026-11-03', '14:00'], ['2026-11-03', '18:00']]);
    // 同じ公演の 2 回は、同じ作品として自動でまとまる（起案者の指示 2026-10-19「回は違っても同じ作品なら同じ作品のツリーとして統合する
    // 作業を自動でやって」、diary.autoMerge）。早い回（昼）に夜の回がまとまる
    const night = works().find(w => w.time === '18:00').work_key, day = works().find(w => w.time === '14:00').work_key;
    assert.deepEqual(sqlite.prepare('SELECT work_key, into_key FROM merges').all().map(r => [r.work_key, r.into_key]), [[night, day]]);
    // 行かなかった回を消す（まとめを外す → 外す → 完全に取り消す）と、その回の券も消え、作り直さない
    assert.equal((await step(env, a, {post: '/api/merge_work', body: {work_key: day, unmerge: true}})).status, 200);
    assert.equal((await step(env, a, {post: '/api/drop_work', body: {work_key: night}})).status, 200);
    assert.equal((await step(env, a, {post: '/api/purge_work', body: {key: night}})).status, 200);
    await screen(env, a, 'unrated');
    assert.deepEqual(works().map(w => w.time), ['14:00']);
    assert.equal(sqlite.prepare("SELECT count(*) AS n FROM ticket WHERE stage_id='101' AND date='2026-11-03'").get().n, 1);
    // 11/5 が過ぎると、その回も
    env.CLOCK = {today: '2026-11-06', now: Date.parse('2026-11-06T03:00:00Z')};
    await screen(env, a, 'unrated');
    assert.deepEqual(works().map(w => [w.first_date, w.time]), [['2026-11-03', '14:00'], ['2026-11-05', '']]);
  } finally { sqlite.close(); }
});

// 起案者の指示 2026-10-18「購入済み公演は、観に行く日の公演開始時間過ぎてから未評価に移して」。前は行く日の 0 時に購入済の公演から消え、
// 未評価には開演を過ぎてから入るので、その日の開演まではどちらにも出なかった
test('購入済の公演は、行く日の開演を過ぎるまで購入済に残り、過ぎたら未評価に移る', async () => {
  const {env, sqlite} = withIndex();
  const a = await signIn(env);
  try {
    await step(env, a, {post: '/api/react', body: {stage_id: '101', value: 'owned', nofill: true}});
    assert.equal((await step(env, a, {post: '/api/ticket', body: {stage_id: '101', date: '2026-11-03', time: '14:00'}})).status, 200);
    sqlite.prepare("UPDATE ticket SET confirmed=1 WHERE stage_id='101'").run();
    // 11/3 の 13:00（日本時間）: まだ購入済
    env.CLOCK = {today: '2026-11-03', now: Date.parse('2026-11-03T04:00:00Z')};
    assert.match((await screen(env, a, 'tickets')).body_html, /data-stage="101"/);
    assert.doesNotMatch((await screen(env, a, 'unrated')).body_html, /舞台ひとつめ/);
    // 14:30: 未評価へ
    env.CLOCK = {today: '2026-11-03', now: Date.parse('2026-11-03T05:30:00Z')};
    assert.doesNotMatch((await screen(env, a, 'tickets')).body_html, /data-stage="101"/);
    assert.match((await screen(env, a, 'unrated')).body_html, /舞台ひとつめ/);
  } finally { sqlite.close(); }
});
