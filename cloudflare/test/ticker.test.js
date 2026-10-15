// 電光掲示板（screens/ticker.js）: 今週開幕する公演と、作り置きのおすすめの上位 3 件。
// 起案者の指示（2026-10-15）「今週開幕する公演を電車の電光掲示板みたいにメニューに流す…あと今週のおすすめ上位3件」
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {setup, step, signIn} from './screens/harness.js';

const here = p => new URL(p, import.meta.url).pathname;
const FIXTURE = JSON.parse(execFileSync('python3', [here('./screens/recommend_fixture.py')], {encoding: 'utf8', maxBuffer: 64 * 1024 * 1024}));

test('the ticker lists this week\'s openings and the cached top 3, and nothing for an empty week', async () => {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  const a = await signIn(env);
  try {
    const empty = (await step(env, a, {get: '/api/screen/ticker'})).body;
    assert.deepEqual(empty.ticker, {open: [], recs: []});
    // A stage only in the catalogue opening this week (today is 2026-10-12 in the harness), and one next month.
    sqlite.prepare("INSERT INTO catalogue(id,title,date,venue,url,metadata) VALUES('901','今週あく舞台','2026-10-15','劇場Q','',?)").run(JSON.stringify({end_date: '2026-10-20'}));
    sqlite.prepare("INSERT INTO catalogue(id,title,date,venue,url,metadata) VALUES('902','来月の舞台','2026-11-20','劇場Q','',?)").run(JSON.stringify({end_date: '2026-11-25'}));
    // The recommendations are read from the cache only (never computed here).
    const uid = sqlite.prepare('SELECT id FROM users').get().id;
    sqlite.prepare('INSERT INTO rec_cache(user_id,stamp,body,created_at) VALUES(?,?,?,0)')
      .run(uid, 'x', JSON.stringify({groups: [{stage_id: '101'}, {stage_id: '102'}, {stage_id: '106'}, {stage_id: '104'}]}));
    const t = (await step(env, a, {get: '/api/screen/ticker'})).body.ticker;
    assert.deepEqual(t.open.map(o => [o.title, o.label, o.venue]), [['今週あく舞台', '10/15（木）', '劇場Q']]);
    assert.deepEqual(t.recs.map(r => r.title), ['舞台ひとつめ', '舞台ふたつめ', '劇場の無い舞台']);
  } finally { sqlite.close(); }
});
