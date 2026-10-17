// 探す（起案者の指示 2026-10-17「カードがない新しい公演も検索で出るようにして」「ワードが入って検索されてるなら、
// 次のところも該当件数のみ表示されるようにして」、「ふぉ〜ゆ〜」で 0 件だった）。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {setup, step, signIn} from './screens/harness.js';

const here = p => new URL(p, import.meta.url).pathname;
const FIXTURE = JSON.parse(execFileSync('python3', [here('./screens/recommend_fixture.py')], {encoding: 'utf8', maxBuffer: 64 * 1024 * 1024}));
const search = (env, a, q, more = '') => step(env, a, {get: '/api/screen/search?q=' + encodeURIComponent(q) + more}).then(r => r.body.body_html);

test('stages without a card are found: in the index, and only in the catalogue; a wave dash matches either way', async () => {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  sqlite.exec("DELETE FROM rec_card WHERE stage_id='101'");
  const meta = JSON.stringify({end_date: '2099-12-31', group: '劇団新', fields: {'出演': '越岡裕貴（ふぉ～ゆ～）'}});
  sqlite.prepare('INSERT INTO catalogue(id,title,date,venue,url,metadata) VALUES(?,?,?,?,?,?)').run('990001', 'メイユール・ソワレ', '2099-12-01', '博品館劇場', '', meta);
  const a = await signIn(env);
  try {
    const idx = await search(env, a, 'ひとつめ');
    assert.match(idx, /<article class="ticket recommend" data-stage="101"/);
    const cat = await search(env, a, 'ふぉ〜ゆ〜');          // typed with U+301C; the data has U+FF5E
    assert.match(cat, /<article class="ticket recommend" data-stage="990001"/);
    assert.match(cat, /これから観られる公演 1 件/);
    // The tabs and the calendar below count only what the word hits.
    assert.match(cat, /これから観られる公演<span class="mn">1<\/span>/);
    assert.match(cat, /aria-label="2099 年 12 月 1 件"/);
    assert.match(cat, /観た記録<span class="mn">0<\/span>/);
    assert.match(cat, /「ふぉ〜ゆ〜」に当たったものだけを数えています/);
    // The recommend screen's box finds it too.
    const rec = (await step(env, a, {get: '/api/screen/recommend?find=' + encodeURIComponent('ふぉ〜ゆ〜')})).body.body_html;
    assert.match(rec, /data-stage="990001"/);
  } finally { sqlite.close(); }
});

test('with a word, the 観た記録 calendar counts only the records it hits; with no hit it shows zeros instead of vanishing', async () => {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  const a = await signIn(env);
  try {
    for (const [title, date] of [['夏の夜の夢', '2025-10-05'], ['冬物語', '2025-11-02'], ['夏の終わり', '2024-07-01']])
      assert.ok((await step(env, a, {post: '/api/add_work', body: {title, date}})).body.work_key);
    const all = await search(env, a, '', '&cal=past');
    assert.match(all, /観た記録<span class="mn">3<\/span>/);
    const hit = await search(env, a, '夏', '&cal=past');
    assert.match(hit, /観た記録<span class="mn">2<\/span>/);
    assert.match(hit, /aria-label="2025 年 10 月 1 件"/);
    assert.match(hit, /aria-label="2024 年 7 月 1 件"/);
    assert.doesNotMatch(hit, /aria-label="2025 年 11 月/);
    const none = await search(env, a, 'ふぉ〜ゆ〜', '&cal=past');
    assert.match(none, /観た記録<span class="mn">0<\/span>/);
    assert.match(none, /これから観られる公演<span class="mn">0<\/span>/);
  } finally { sqlite.close(); }
});
