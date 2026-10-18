// 出さない語（起案者の指摘 2026-10-16「出さない語が反映されてない。出さない語はおすすめ画面で設定できるようにしてほしい」）。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {setup, step, signIn} from './screens/harness.js';

const here = p => new URL(p, import.meta.url).pathname;
const FIXTURE = JSON.parse(execFileSync('python3', [here('./screens/recommend_fixture.py')], {encoding: 'utf8', maxBuffer: 64 * 1024 * 1024}));

async function rateSeen(env, cookie, title, date, sid, verdict) {
  const key = (await step(env, cookie, {post: '/api/add_work', body: {title, date}})).body.work_key;
  assert.equal((await step(env, cookie, {post: '/api/link_stage', body: {work_key: key, stage_id: sid}})).status, 200);
  assert.equal((await step(env, cookie, {post: '/api/rate', body: {work_key: key, verdict}})).status, 200);
}

for (const word of ['ひとつめ', '俳優乙', 'オリジナル']) {
  test(`a word not to show hides the stage, also when it is only a kind of reason (${word})`, async () => {
    const {env, sqlite} = setup();
    for (const s of FIXTURE.sql) sqlite.exec(s);
    const a = await signIn(env);
    try {
      await rateSeen(env, a, '終わった舞台', '2026-08-05', '103', '◎');
      await rateSeen(env, a, '一日だけの舞台', '2026-09-05', '104', '×');
      const before = (await step(env, a, {get: '/api/screen/recommend'})).body.body_html;
      assert.match(before, /data-stage="101"/);
      if (word === 'オリジナル') {
        // The fixture's cards do not carry the kind tag in their text: only the index has it.
        assert.equal(sqlite.prepare("SELECT count(*) AS n FROM rec_card WHERE stage_id='101' AND instr(blob, 'オリジナル')>0").get().n, 0);
      }
      // The box is on the recommend screen itself.
      assert.match(before, /<details class="pbox" id="declined">[\s\S]*<button data-dec="add">追加する<\/button>/);
      assert.equal((await step(env, a, {post: '/api/decline', body: {action: 'add', word}})).status, 200);
      const after = (await step(env, a, {get: '/api/screen/recommend'})).body.body_html;
      assert.doesNotMatch(after, /data-stage="101"/);
      assert.ok(after.includes(`<span class="tag" data-word="${word}">「${word}」<button data-dec="remove">✕</button></span>`));
      assert.equal((await step(env, a, {post: '/api/decline', body: {action: 'remove', word}})).status, 200);
      assert.match((await step(env, a, {get: '/api/screen/recommend'})).body.body_html, /data-stage="101"/);
    } finally { sqlite.close(); }
  });
}

// 対象を選んで入れる出さない語（起案者の指示 2026-10-18）: 選んだ欄にだけ当てる
test('a word with a target hides the stage only when that field has it', async () => {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  const a = await signIn(env);
  try {
    await rateSeen(env, a, '終わった舞台', '2026-08-05', '103', '◎');
    await rateSeen(env, a, '一日だけの舞台', '2026-09-05', '104', '×');
    const rec = async () => (await step(env, a, {get: '/api/screen/recommend'})).body.body_html;
    assert.match(await rec(), /<select id="dec-kind" aria-label="使わない言葉の対象"><option value="">すべて<\/option><option value="題名">題名<\/option>/);
    // 「ひとつめ」は題名にあるが、人の名前ではない
    assert.equal((await step(env, a, {post: '/api/decline', body: {action: 'add', word: 'ひとつめ', kind: '団体'}})).status, 200);
    assert.match(await rec(), /data-stage="101"/);
    assert.equal((await step(env, a, {post: '/api/decline', body: {action: 'add', word: 'ひとつめ', kind: '題名'}})).status, 200);
    const html = await rec();
    assert.doesNotMatch(html, /data-stage="101"/);
    assert.ok(html.includes('<span class="tag" data-word="題名\tひとつめ">題名「ひとつめ」<button data-dec="remove">✕</button></span>'));
    assert.deepEqual(JSON.parse(sqlite.prepare("SELECT value FROM app_setting WHERE key='declined'").get().value), ['団体\tひとつめ', '題名\tひとつめ']);
    // 外すときは控えの形のまま届く
    assert.equal((await step(env, a, {post: '/api/decline', body: {action: 'remove', word: '題名\tひとつめ'}})).status, 200);
    assert.match(await rec(), /data-stage="101"/);
    assert.equal((await step(env, a, {post: '/api/decline', body: {action: 'add', word: 'x', kind: '天気'}})).status, 400);
  } finally { sqlite.close(); }
});
