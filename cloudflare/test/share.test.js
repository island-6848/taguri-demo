// 共有リンク（share.js、dec-share-links）: 本人が選んだものだけを、リンクを知る人にログインなしで見せる。
// 評価・感想・名前は共有するときに選び、既定は出さない。検索エンジンには載せない。取り消すとすぐ開けない。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {setup, step, signIn} from './screens/harness.js';
import {newToken, publicHtml} from '../src/share.js';

const here = p => new URL(p, import.meta.url).pathname;
const FIXTURE = JSON.parse(execFileSync('python3', [here('./screens/recommend_fixture.py')], {encoding: 'utf8', maxBuffer: 64 * 1024 * 1024}));
function withIndex() {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  return {env, sqlite};
}
async function rateSeen(env, u, title, date, sid, verdict) {
  const key = (await step(env, u, {post: '/api/add_work', body: {title, date}})).body.work_key;
  assert.equal((await step(env, u, {post: '/api/link_stage', body: {work_key: key, stage_id: sid}})).status, 200);
  assert.equal((await step(env, u, {post: '/api/rate', body: {work_key: key, verdict}})).status, 200);
  return key;
}
const share = (env, u, body) => step(env, u, {post: '/api/share', body: {action: 'create', ...body}});
const open = async (env, path) => {
  const {default: worker} = await import('../src/worker.js');
  const res = await worker.fetch(new Request('https://taguri.test' + path), env);
  return {status: res.status, headers: res.headers, text: await res.text()};
};
// 公開ページに出てよい道は、ログイン・自分の画像・CSS・CoRich だけ
const internalLinks = html => [...html.matchAll(/(?:href|src)="([^"]*)"/g)].map(m => m[1])
  .filter(u => !/^(\/login|\/s\/[A-Za-z0-9_-]{22}\/poster|\/(style|theme|fonts)\.css|https:\/\/|data:image\/)/.test(u));

test('a token is 22 unguessable characters', () => {
  const t = newToken();
  assert.match(t, /^[A-Za-z0-9_-]{22}$/);
  assert.notEqual(newToken(), t);
});

test('a stage card is public by link only, carries no record by default, and stops at once when revoked', async () => {
  const {env, sqlite} = withIndex();
  const a = await signIn(env);
  try {
    const key = await rateSeen(env, a, '舞台ひとつめ', '2026-08-01', '101', '◎');
    sqlite.prepare('UPDATE works SET note_impression=? WHERE work_key=?').run('ひみつの感想', key);
    assert.equal((await share(env, a, {kind: 'stage', stage_id: '101', label: 'nope'})).status, 400);
    assert.equal((await share(env, a, {kind: 'stage', stage_id: 'none', label: 'owned'})).status, 400);
    const made = await share(env, a, {kind: 'stage', stage_id: '101', label: 'watched'});
    assert.equal(made.status, 200);
    assert.match(made.body.path, /^\/s\/[A-Za-z0-9_-]{22}$/);
    // ログインしていない人が開ける。検索エンジンには載せない。スクリプトは動かさない
    const pub = await open(env, made.body.path);
    assert.equal(pub.status, 200);
    assert.match(pub.text, /この公演を観ました！/);
    assert.match(pub.text, /舞台ひとつめ|舞台/);
    assert.match(pub.headers.get('x-robots-tag'), /noindex/);
    assert.match(pub.text, /<meta name="robots" content="noindex/);
    assert.match(pub.headers.get('content-security-policy'), /script-src 'none'/);
    assert.match(pub.text, /property="og:title" content="この公演を観ました！『/);
    // 評価・感想・利用者は出さない（選んでいない）
    assert.doesNotMatch(pub.text, /ひみつの感想|◎/);
    const uid = sqlite.prepare('SELECT user_id FROM works WHERE work_key=?').get(key).user_id;
    assert.ok(!pub.text.includes(uid) && !pub.text.includes(key));
    assert.deepEqual(internalLinks(pub.text), []);
    // 選べば、評価と感想が出る
    const full = await share(env, a, {kind: 'stage', stage_id: '101', label: 'watched', verdict: true, note: true});
    const pub2 = await open(env, full.body.path);
    assert.match(pub2.text, /評価 <b>◎<\/b>/);
    assert.match(pub2.text, /ひみつの感想/);
    // 取り消すと、すぐ開けない。ほかの人は取り消せない
    const b = await signIn(env);
    const token = made.body.path.slice(3);
    assert.equal((await step(env, b, {post: '/api/share', body: {action: 'revoke', token}})).status, 400);
    assert.equal((await step(env, a, {post: '/api/share', body: {action: 'revoke', token}})).status, 200);
    assert.equal((await open(env, made.body.path)).status, 404);
    assert.equal((await open(env, '/s/' + 'x'.repeat(22))).status, 404);
  } finally { sqlite.close(); }
});

test('the pages show the record list, the overview, favourites and the chronicle with only what was chosen', async () => {
  const {env, sqlite} = withIndex();
  const a = await signIn(env);
  try {
    const key = await rateSeen(env, a, '舞台ひとつめ', '2026-08-01', '101', '◎');
    await rateSeen(env, a, '一日だけの舞台', '2026-09-05', '104', '×');
    sqlite.prepare('UPDATE works SET note_impression=? WHERE work_key=?').run('ひみつの感想', key);
    await step(env, a, {post: '/api/favourite', body: {action: 'add', kind: '人', name: '俳優甲'}});
    const uid = sqlite.prepare('SELECT user_id FROM works WHERE work_key=?').get(key).user_id;
    sqlite.prepare("INSERT INTO app_setting(user_id,key,value,updated_at) VALUES(?, 'display_name', 'たぐ子', 'x')").run(uid);
    for (const kind of ['works', 'records', 'favourites', 'chronicle']) {
      const made = await share(env, a, {kind});
      assert.equal(made.status, 200, kind);
      const pub = await open(env, made.body.path);
      assert.equal(pub.status, 200, kind);
      assert.doesNotMatch(pub.text, /ひみつの感想|__TAGURI_TOKEN__|たぐ子/, kind);
      assert.ok(!pub.text.includes(uid) && !pub.text.includes(key), kind);
      assert.deepEqual(internalLinks(pub.text), [], kind);
      if (kind === 'works') {
        assert.match(pub.text, /舞台ひとつめ/);
        assert.match(pub.text, /2026\/08\/01/);
        assert.doesNotMatch(pub.text, /share-verdict/);
      }
      if (kind === 'favourites') assert.match(pub.text, /俳優甲/);
    }
    // 評価・感想・名前を選んだ一覧
    const full = await share(env, a, {kind: 'works', verdict: true, note: true, name: true});
    const pub = await open(env, full.body.path);
    assert.match(pub.text, /share-verdict">◎/);
    assert.match(pub.text, /ひみつの感想/);
    assert.match(pub.text, /<b>たぐ子<\/b> さんの共有/);
    // 本人の一覧（設定の画面）と、取り消した記録は出ない
    const list = await step(env, a, {post: '/api/share', body: {action: 'list'}});
    assert.equal(list.body.shares.length, 5);
    assert.equal((await step(env, a, {post: '/api/drop_work', body: {work_key: key}})).status, 200);
    assert.doesNotMatch((await open(env, full.body.path)).text, /舞台ひとつめ/);
  } finally { sqlite.close(); }
});

test('the public pages strip actions and internal links from the panels', () => {
  const html = publicHtml('<a href="/records/works?t=__TAGURI_TOKEN__#w-1">題</a><button data-x="1">押す</button><script>alert(1)</script>'
    + '<a href="https://stage.corich.jp/stage/1">CoRich</a><div data-work="k1">中</div>');
  assert.equal(html, '<span>題</span><a href="https://stage.corich.jp/stage/1">CoRich</a><div>中</div>');
});

test('one person keeps at most 100 links, and deleting the account removes them', async () => {
  const {env, sqlite} = withIndex();
  const a = await signIn(env);
  try {
    const first = await share(env, a, {kind: 'works'});
    const uid = sqlite.prepare('SELECT user_id FROM share').get().user_id;
    const ins = sqlite.prepare("INSERT INTO share(token,user_id,kind,created_at) VALUES(?,?,'works','x')");
    for (let i = 1; i < 100; i++) ins.run(String(i).padStart(22, 'a'), uid);
    const over = await share(env, a, {kind: 'works'});
    assert.equal(over.status, 400);
    assert.match(over.body.error, /100 件まで/);
    assert.equal((await open(env, first.body.path)).status, 200);
    sqlite.exec(`PRAGMA foreign_keys=ON; DELETE FROM users WHERE id='${uid}'`);
    assert.equal(sqlite.prepare('SELECT count(*) AS n FROM share').get().n, 0);
  } finally { sqlite.close(); }
});

test('a diary row shares as a watched card through its record, and a record without a stage is refused', async () => {
  const {env, sqlite} = withIndex();
  const a = await signIn(env);
  try {
    const key = await rateSeen(env, a, '舞台ひとつめ', '2026-08-01', '101', '○');
    const made = await share(env, a, {kind: 'stage', label: 'watched', work_key: key, verdict: true});
    assert.equal(made.status, 200);
    assert.match((await open(env, made.body.path)).text, /評価 <b>○<\/b>/);
    const bare = (await step(env, a, {post: '/api/add_work', body: {title: '結び付いていない舞台', date: '2026-08-02'}})).body.work_key;
    const no = await share(env, a, {kind: 'stage', label: 'watched', work_key: bare});
    assert.equal(no.status, 400);
    assert.match(no.body.error, /結び付いていません/);
    // ほかの人の記録の鍵では作れない
    const b = await signIn(env);
    assert.equal((await share(env, b, {kind: 'stage', label: 'watched', work_key: key})).status, 400);
  } finally { sqlite.close(); }
});

test('the cards and pages carry the share buttons, and settings lists the links', async () => {
  const {env, sqlite} = withIndex();
  const a = await signIn(env);
  try {
    await rateSeen(env, a, '舞台ひとつめ', '2026-08-01', '101', '◎');
    await step(env, a, {post: '/api/favourite', body: {action: 'add', kind: '人', name: '俳優甲'}});   // 空のお気に入りには押し口を出さない
    for (const name of ['records', 'chronicle', 'favourites']) {
      assert.match((await step(env, a, {get: '/api/screen/' + name})).body.body_html, new RegExp(`data-share-kind="${name}"`), name);
    }
    // 興味ありのカード（これからの公演 102）
    sqlite.exec("UPDATE rec_stage SET start='2026-12-01', end='2026-12-10' WHERE stage_id='102'");
    assert.equal((await step(env, a, {post: '/api/react', body: {stage_id: '102', value: 'interest', nofill: true}})).status, 200);
    assert.match((await step(env, a, {get: '/api/screen/interest'})).body.body_html,
      /data-share-kind="stage" data-share-stage="102" data-share-label="interest" aria-label="この公演を共有" title="共有"><svg[\s\S]*?<\/button><\/article>/);
    await share(env, a, {kind: 'works'});
    const set = (await step(env, a, {get: '/api/screen/settings'})).body.body_html;
    assert.match(set, /共有中のリンク（1 件）/);
    assert.match(set, /data-share-revoke="[A-Za-z0-9_-]{22}"/);
  } finally { sqlite.close(); }
});
