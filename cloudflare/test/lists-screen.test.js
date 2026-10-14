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
    assert.match(next, /<li class="dgli und" data-stage="101">/);
    assert.match(next, /<input type="hidden" name="w" value="next">/);
    await step(env, a, {post: '/api/react', body: {stage_id: '101', value: 'interest', nofill: true}});
    assert.match((await screen(env, a, 'reminder', '?w=next')).body_html, /<li class="dgli trk" data-stage="101">/);
    // The filter chosen here applies to おすすめ too.
    await screen(env, a, 'reminder', '?w=next&f=1&pref=' + encodeURIComponent('大阪府'));
    assert.match((await screen(env, a, 'recommend')).body_html, /いまは<b>大阪府（1 県）<\/b>/);
  } finally { sqlite.close(); }
});
