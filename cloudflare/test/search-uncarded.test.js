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
    assert.match(cat, /今後の公演 1 件/);
    // The tabs and the calendar below count only what the word hits.
    assert.match(cat, /今後の公演<span class="mn">1<\/span>/);
    assert.match(cat, /aria-label="2099 年 12 月 1 件"/);
    assert.match(cat, /観た記録<span class="mn">0<\/span>/);
    assert.match(cat, /「ふぉ〜ゆ〜」に当たったものだけを数えています/);
    // The recommend screen has no search box of its own any more (起案者の指示 2026-10-17): ?find is ignored.
    const rec = (await step(env, a, {get: '/api/screen/recommend?find=' + encodeURIComponent('ふぉ〜ゆ〜')})).body.body_html;
    assert.doesNotMatch(rec, /data-stage="990001"|rfind/);
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
    assert.match(none, /今後の公演<span class="mn">0<\/span>/);
  } finally { sqlite.close(); }
});

test('past stages (2019-) show on 探す by title prefix, with 観た and 行けばよかった', async () => {
  const {env, sqlite} = setup();
  const ins = sqlite.prepare('INSERT INTO past_stage(stage_id,title,tkey,start,end,venue,grp,pref,people) VALUES(?,?,?,?,?,?,?,?,?)');
  ins.run('700001', '夏の夜の夢', '夏の夜の夢', '2023-07-01', '2023-07-10', '劇場A', '劇団甲', '東京都', '[["出演","俳優甲"]]');
  ins.run('700002', '夏の夜の夢', '夏の夜の夢', '2023-08-01', '2023-08-03', '劇場B', '劇団甲', '大阪府', '[["出演","俳優甲"]]');   // the tour: one row
  ins.run('700003', '夏の夜の夢 再演', '夏の夜の夢再演', '2025-05-01', '2025-05-05', '劇場C', '劇団乙', '東京都', '[]');
  ins.run('700004', '冬物語', '冬物語', '2024-01-01', '2024-01-05', '劇場D', '劇団丙', '東京都', '[]');
  const a = await signIn(env);
  try {
    const html = await search(env, a, '夏の夜');
    assert.match(html, /<h2>過去の公演（2019 年〜） 2 件<\/h2>/);
    assert.match(html, /data-stage="700003" data-title="夏の夜の夢 再演"[\s\S]*?data-stage="700001" data-title="夏の夜の夢"/);   // newest first
    assert.match(html, /2023\/7\/1〜2023\/8\/3・劇場A ほか 1 会場/);
    assert.match(html, /<button type="button" data-past="seen">観た<\/button><button type="button" data-past="missed">行けばよかった<\/button>/);
    // 観た: the date (within the run) and the curtain time, then 観劇記録に追加
    assert.match(html, /<div class="past-seen" hidden><label>観た日 <input type="date" name="date" value="" min="2023-07-01" max="2023-08-03" required><\/label><label>劇場 <select name="stage"><option value="700001" data-start="2023-07-01" data-end="2023-07-10" data-venue="劇場A">劇場A（2023\/7\/1〜2023\/7\/10）<\/option><option value="700002" data-start="2023-08-01" data-end="2023-08-03" data-venue="劇場B">劇場B（2023\/8\/1〜2023\/8\/3）<\/option><\/select><\/label><label>開演 <input type="time" name="time" step="60"><\/label><button type="button" data-past="seen-save">観劇記録に追加<\/button><\/div>/);
    assert.doesNotMatch(html, /冬物語/);
    // 観た: into the diary, linked to that stage. The row stays, marked 記録あり, so another visit can be added
    // (起案者の問い 2026-10-21 ── 前はこの一覧から消え、同じ劇場にもう 1 回足せなかった)
    const added = await step(env, a, {post: '/api/add_work', body: {title: '夏の夜の夢', stage_id: '700001', date: '2023-07-08', time: '18:30'}});
    assert.equal(added.status, 200);
    assert.equal(added.body.stage_id, '700001');
    assert.deepEqual({...sqlite.prepare("SELECT first_date, time, stage_id FROM works WHERE title='夏の夜の夢'").get()}, {first_date: '2023-07-08', time: '18:30', stage_id: '700001'});
    const again = await search(env, a, '夏の夜');
    assert.match(again, /data-stage="700001" data-title="夏の夜の夢">\n<div class="past-t"><b>夏の夜の夢<\/b>(?:<span class="past-g">[^<]*<\/span>)?<span class="badge part">記録あり 1 回<\/span>/);
    assert.match(again, /劇場A（2023\/7\/1〜2023\/7\/10）・記録あり 1 回<\/option><option value="700002"[^>]*>劇場B（2023\/8\/1〜2023\/8\/3）<\/option>/);
    assert.match(again, /data-past="seen">観た（もう 1 回追加）<\/button>/);
    // 行けばよかった: the missed list, pointing at the very stage.
    assert.equal((await step(env, a, {post: '/api/missed', body: {title: '夏の夜の夢 再演', stage_id: '700003'}})).status, 200);
    assert.equal(sqlite.prepare("SELECT stage_id FROM missed WHERE title='夏の夜の夢 再演'").get().stage_id, '700003');
    assert.match(await search(env, a, '夏の夜'), /data-past="missed" disabled>行けばよかったに入っています/);
  } finally { sqlite.close(); }
});

test('past stages are found by a person name through the R2 name index (one shard read, no scan)', async () => {
  const {env, sqlite} = setup();
  const {pastShard} = await import('../src/screens/lists.js');
  const name = '俳優甲', file = `pastidx/v1/${pastShard(name).toString(16).padStart(2, '0')}.json`;
  const shard = {v: 1, stages: {'800001': ['ある舞台', 'ある舞台', '2022-03-01', '2022-03-05', '劇場E', '劇団丁']}, names: {[name]: ['800001']}};
  const gets = [];
  env.POSTERS = {get: async key => { gets.push(key); return key === file ? {json: async () => shard} : null; }};
  const a = await signIn(env);
  try {
    const html = await search(env, a, '俳優甲');
    assert.match(html, /data-stage="800001" data-title="ある舞台"/);
    assert.match(html, /ヒットした箇所：出演・作り手・団体/);
    assert.deepEqual([...new Set(gets)], [file]);
  } finally { sqlite.close(); }
});

// 起案者の指摘 2026-10-18「複数日程ツアーのあるような公演で、適切な観劇日を入れても観劇した劇場がその日と対応しない」
test('a tour seen on a date of another venue is linked to the venue playing that day', async () => {
  const {env, sqlite} = setup();
  const ins = sqlite.prepare('INSERT INTO past_stage(stage_id,title,tkey,start,end,venue,grp,pref,people) VALUES(?,?,?,?,?,?,?,?,?)');
  ins.run('710001', '旅の芝居', '旅の芝居', '2023-07-01', '2023-07-10', '劇場A', '劇団甲', '東京都', '[]');
  ins.run('710002', '旅の芝居', '旅の芝居', '2023-08-01', '2023-08-03', '劇場B', '劇団甲', '大阪府', '[]');
  ins.run('710003', '旅の芝居', '旅の芝居', '2023-08-02', '2023-08-02', '劇場X', '劇団乙', '大阪府', '[]');   // another troupe, same title
  const a = await signIn(env);
  try {
    // the row carries the first venue's id, but the date is in 劇場B's run → 劇場B
    const added = await step(env, a, {post: '/api/add_work', body: {title: '旅の芝居', stage_id: '710001', date: '2023-08-02'}});
    assert.equal(added.status, 200);
    assert.equal(added.body.stage_id, '710002');
    assert.deepEqual({...sqlite.prepare("SELECT stage_id, venue FROM works WHERE title='旅の芝居'").get()}, {stage_id: '710002', venue: '劇場B'});
    // a date inside the given venue's run keeps it, and the venue is filled in
    const kept = await step(env, a, {post: '/api/add_work', body: {title: '旅の芝居', stage_id: '710001', date: '2023-07-05'}});
    assert.equal(kept.body.stage_id, '710001');
    assert.equal(sqlite.prepare("SELECT venue FROM works WHERE work_key=?").get(kept.body.work_key).venue, '劇場A');
  } finally { sqlite.close(); }
});

// 起案者の指摘 2026-10-18「連続で何回も同じ公演を追加したい場合に対処して」
test('the same past stage can be added again: another day, or the same day at another curtain time', async () => {
  const {env, sqlite} = setup();
  sqlite.prepare('INSERT INTO past_stage(stage_id,title,tkey,start,end,venue,grp,pref,people) VALUES(?,?,?,?,?,?,?,?,?)')
    .run('720001', '何度も観た', '何度も観た', '2023-07-01', '2023-07-10', '劇場A', '劇団甲', '東京都', '[]');
  const a = await signIn(env);
  const add = body => step(env, a, {post: '/api/add_work', body: {title: '何度も観た', stage_id: '720001', ...body}});
  try {
    assert.equal((await add({date: '2023-07-02', time: '13:00'})).status, 200);
    assert.equal((await add({date: '2023-07-05', time: '13:00'})).status, 200);                 // another day
    const evening = await add({date: '2023-07-02', time: '18:00'});                               // same day, evening show
    assert.equal(evening.status, 200);
    assert.equal(evening.body.work_key.endsWith('#2023-07-02#18:00'), true);
    assert.equal((await add({date: '2023-07-02', time: '18:00'})).status, 400);                 // the very same show twice
    assert.equal((await add({date: '2023-07-05'})).status, 400);                                // same day without a time: ask for it
    assert.equal(sqlite.prepare("SELECT COUNT(*) n FROM works WHERE title='何度も観た' AND stage_id='720001'").get().n, 3);
  } finally { sqlite.close(); }
});

// ツアーは 1 枚にまとめる（起案者の指示 2026-10-20「ツアーがバラバラに出ていて、バラバラに興味ありを押せるようになってしまってる。まとめて」）
test('a tour is one card on 探す: the other venues are on its schedule and in data-tours, and the count is per production', async () => {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  const ins = sqlite.prepare('INSERT INTO catalogue(id,title,date,venue,url,metadata) VALUES(?,?,?,?,?,?)');
  const meta = end => JSON.stringify({end_date: end, group: '劇団旅', fields: {'出演': '旅役者'}});
  ins.run('990101', '旅の公演', '2099-11-01', '劇場東', '', meta('2099-11-05'));
  ins.run('990102', '旅の公演', '2099-11-10', '劇場西', '', meta('2099-11-12'));
  ins.run('990103', '旅の公演', '2099-12-01', '劇場北', '', meta('2099-12-02'));
  const a = await signIn(env);
  try {
    const html = await search(env, a, '旅の公演');
    assert.equal((html.match(/<article class="ticket [^"]*" data-stage="99010\d"/g) || []).length, 1);
    assert.match(html, /<article class="ticket recommend" data-stage="990101" data-tours="990102,990103"/);
    assert.match(html, /今後の公演 1 件/);
  } finally { sqlite.close(); }
});
