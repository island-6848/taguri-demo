// 種類の理由を「使わない」にする（起案者の指示 2026-10-16「自分に合わないなと思うおすすめ理由を消すことはできる？」、q-kind-reason-off）。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {setup, step, signIn} from './screens/harness.js';
import {withoutKinds, reasonRows} from '../src/screens/recommend.js';

const here = p => new URL(p, import.meta.url).pathname;
const FIXTURE = JSON.parse(execFileSync('python3', [here('./screens/recommend_fixture.py')], {encoding: 'utf8', maxBuffer: 64 * 1024 * 1024}));

test('a turned-off kind leaves the people and the other kinds alone', () => {
  const rows = [{verdict: '◎', people: [['出演', 'オリジナル'], ['#原作', 'オリジナル'], ['#形式', 'ミュージカル']]}];
  const got = withoutKinds(rows, new Set(['#原作\toriginal', '#原作\tオリジナル']));
  // A person who happens to have the same name stays; only the kind tag goes.
  assert.deepEqual(got[0].people, [['出演', 'オリジナル'], ['#形式', 'ミュージカル']]);
  assert.equal(withoutKinds(rows, new Set()), rows);
});

test('a kind reason has its own ✕, which is not the person ✕ (that hides the stages)', () => {
  const html = reasonRows({parts: [[0.5, '出演', '甲', 1]], kinds: [[0.2, '#原作', 'オリジナル', 1]]}, new Map());
  assert.match(html, /<button class="rsx" data-kindoff="#原作\tオリジナル" title="この理由をおすすめに使わない（公演は消さない）">✕<\/button>/);
  assert.match(html, /<button class="rsx" data-word="甲"/);
});

async function rateSeen(env, cookie, title, date, sid, verdict) {
  const key = (await step(env, cookie, {post: '/api/add_work', body: {title, date}})).body.work_key;
  assert.equal((await step(env, cookie, {post: '/api/link_stage', body: {work_key: key, stage_id: sid}})).status, 200);
  assert.equal((await step(env, cookie, {post: '/api/rate', body: {work_key: key, verdict}})).status, 200);
}

test('turning a kind reason off takes it out of the reasons and the score, for this user only, and it can be put back', async () => {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  const a = await signIn(env), b = await signIn(env);
  try {
    for (const u of [a, b]) {
      await rateSeen(env, u, '終わった舞台', '2026-08-05', '103', '◎');
      await rateSeen(env, u, '一日だけの舞台', '2026-09-05', '104', '×');
    }
    const before = (await step(env, a, {get: '/api/screen/recommend'})).body.body_html;
    const m = /data-kindoff="([^"]+)"/.exec(before);
    assert.ok(m, 'a kind reason is shown before');
    const key = m[1].replace('&amp;', '&');
    const [axis, tag] = key.split('\t');
    assert.equal((await step(env, a, {post: '/api/kind_off', body: {action: 'add', key}})).status, 200);
    const after = (await step(env, a, {get: '/api/screen/recommend'})).body.body_html;
    assert.ok(!after.includes(`data-kindoff="${m[1]}"`), 'the reason is gone');
    assert.match(after, /<article class="ticket recommend" data-stage="101"/);       // the stage itself stays (its people)
    // The other user still has it.
    assert.ok((await step(env, b, {get: '/api/screen/recommend'})).body.body_html.includes(`data-kindoff="${m[1]}"`));
    // The list of kinds turned off lives on おすすめ (its 選び方 row), not on お気に入り (起案者の指示 2026-10-17).
    const fav = (await step(env, a, {get: '/api/screen/favourites'})).body.body_html;
    assert.doesNotMatch(fav, /id="kind-off"/);
    assert.match(after, /<div class="fil2 tune">[\s\S]*<details class="pbox" id="kind-off">[\s\S]*使わない理由 <b>1件<\/b>/);
    assert.ok(after.includes(`「${tag}」<button data-kindoff-remove="1">✕</button>`), axis);
    assert.doesNotMatch((await step(env, b, {get: '/api/screen/recommend'})).body.body_html, /id="kind-off"/);
    assert.equal((await step(env, a, {post: '/api/kind_off', body: {action: 'remove', key}})).status, 200);
    assert.ok((await step(env, a, {get: '/api/screen/recommend'})).body.body_html.includes(`data-kindoff="${m[1]}"`));
    // Only '#axis<TAB>tag' keys are taken.
    assert.equal((await step(env, a, {post: '/api/kind_off', body: {action: 'add', key: 'オリジナル'}})).status, 400);
  } finally { sqlite.close(); }
});

// 札の表示は「種類」から「形式」に（起案者の指示 2026-10-18「『種類』ってよりは形式？って表現近いと思う」）
test('原作の国 is a kind reason with its own label (no 出典), and can be turned off like the others', () => {
  const html = reasonRows({parts: [], kinds: [[0.3, '#原作の国', '韓国', 2]]}, new Map());
  assert.match(html, /<span class="net">形式<\/span>原作の国 <b>韓国<\/b>/);
  assert.doesNotMatch(html, /出典/);
  assert.match(html, /data-kindoff="#原作の国\t韓国"/);
});

test('原作 shows the kind of source without repeating the heading; no price band reason', () => {
  const html = reasonRows({parts: [], kinds: [[0.3, '#原作', '漫画原作', 2], [0.2, '#原作', 'オリジナル', 1]]}, new Map());
  assert.match(html, /<span class="net">形式<\/span><b>漫画原作<\/b>/);
  assert.match(html, /<span class="net">形式<\/span>原作 <b>オリジナル<\/b>/);
  assert.doesNotMatch(html, /出典/);
});

test('原作「原作もの」 left in the production index is neither a reason nor a score', async () => {
  const {droppedKind} = await import('../src/recommend.js');
  assert.ok(droppedKind('#原作', '原作もの') && droppedKind('#値段', '5千円未満'));
  assert.ok(!droppedKind('#原作', '漫画原作') && !droppedKind('#原作', 'オリジナル'));
  const html = reasonRows({parts: [], kinds: [[0.3, '#原作', '原作もの', 2], [0.2, '#形式', 'ミュージカル', 1]]}, new Map());
  assert.doesNotMatch(html, /原作もの/);
  assert.match(html, /<span class="net">形式<\/span><b>ミュージカル<\/b>/);   // 札と同じ見出し「形式」は重ねない
  assert.doesNotMatch(html, /種類/);
});
