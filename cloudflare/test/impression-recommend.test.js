// 感想で書いた特徴への好みが、本人のおすすめの順位と理由に効く（#104、起案者の指示 2026-10-18
// 「感想で書いた内容を推薦に反映させるところまで」）。書き換え・削除は次の計算で効き、ほかの人には効かない。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {setup, step, signIn} from './screens/harness.js';
import {rankedGroups, reasonRows} from '../src/screens/recommend.js';

const here = p => new URL(p, import.meta.url).pathname;
const FIXTURE = JSON.parse(execFileSync('python3', [here('./screens/recommend_fixture.py')], {encoding: 'utf8', maxBuffer: 64 * 1024 * 1024}));

async function rateSeen(env, cookie, title, date, sid, verdict) {
  const key = (await step(env, cookie, {post: '/api/add_work', body: {title, date}})).body.work_key;
  assert.equal((await step(env, cookie, {post: '/api/link_stage', body: {work_key: key, stage_id: sid}})).status, 200);
  assert.equal((await step(env, cookie, {post: '/api/rate', body: {work_key: key, verdict}})).status, 200);
  return key;
}

test('a note on a seen show moves the shows with the same kind word, and editing or deleting it moves them back', async () => {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  const ver = sqlite.prepare("SELECT v FROM rec_meta WHERE k='current'").get().v;
  // × を付けた 104 と、これからの 101・人の手がかりの無い 199 に「家族」。全体は × でも、感想では家族の描写を好きと書く
  sqlite.exec(`INSERT INTO rec_stage(ver,stage_id,title,tkey,grp,tour,gkey,start,end,credits,entry) VALUES('${ver}','199','家族の舞台','家族の舞台','劇団戊','t199','劇団戊','2026-12-01','2026-12-05','[]','{"title": "家族の舞台", "pref": "東京都"}')`);
  for (const sid of ['101', '104', '199']) sqlite.exec(`INSERT INTO rec_credit(ver,role,person,stage_id,role_w,role_group) VALUES('${ver}','#題材','家族','${sid}',1.0,'theme')`);
  // 観た公演の種類の言葉は rec_people から読む（ratedWorks → peopleFor）
  const row = sqlite.prepare('SELECT people FROM rec_people WHERE ver=? AND stage_id=?').get(ver, '104');
  if (row) sqlite.prepare('UPDATE rec_people SET people=? WHERE ver=? AND stage_id=?').run(JSON.stringify([...JSON.parse(row.people), ['#題材', '家族']]), ver, '104');
  else sqlite.prepare('INSERT INTO rec_people(ver,stage_id,people) VALUES(?,?,?)').run(ver, '104', JSON.stringify([['#題材', '家族']]));
  const a = await signIn(env), b = await signIn(env);
  try {
    const keys = {};
    for (const u of [a, b]) {
      await rateSeen(env, u, '終わった舞台', '2026-08-05', '103', '◎');
      keys[u] = await rateSeen(env, u, '一日だけの舞台', '2026-09-05', '104', '×');
    }
    // 作品の鍵は利用者をまたいで同じなので、利用者は記録を付けた順（a が先）に引く
    const [uidA, uidB] = sqlite.prepare('SELECT user_id FROM works GROUP BY user_id ORDER BY min(rowid)').all().map(r => r.user_id);
    const uidOf = {[a]: uidA, [b]: uidB};
    // 控えの印は works の更新時刻（秒）なので、書き込みのたびに時計を進める（試験の時計は止まっている）
    const note = async (u, text) => { env.CLOCK.now += 1000; return (await step(env, u, {post: '/api/note', body: {work_key: keys[u], note_impression: text}})).status; };
    const ranked = async u => {
      const r = await rankedGroups({db: env.DB, env, uid: uidOf[u], today: env.CLOCK.today, now: env.CLOCK.now});
      return r.groups.map(g => [g.stage_id, g.imp ? g.imp.map(([label, sign]) => label + sign) : []]);
    };
    const before = await ranked(a);
    assert.ok(!before.some(([sid]) => sid === '199'), 'no reason for 199 without the note');
    assert.equal(await note(a, '家族の描写が好きだった。'), 200);
    const liked = await ranked(a);
    assert.deepEqual(liked.find(([sid]) => sid === '199'), ['199', ['家族1']], 'a show with only the liked kind joins');
    assert.deepEqual(liked.find(([sid]) => sid === '101'), ['101', ['家族1']]);
    assert.deepEqual(await ranked(b), before, 'the other user is not moved');
    // 苦手と書き直すと、点の無い公演は加えず、点のある公演の理由は向きが変わる
    assert.equal(await note(a, '家族の話は苦手だった。'), 200);
    const disliked = await ranked(a);
    assert.ok(!disliked.some(([sid]) => sid === '199'));
    assert.deepEqual(disliked.find(([sid]) => sid === '101'), ['101', ['家族-1']]);
    assert.equal(await note(a, ''), 200);
    assert.deepEqual(await ranked(a), before, 'deleting the note puts the ranking back');
  } finally { sqlite.close(); }
});

test('the reason line quotes the user\'s own note, escaped', () => {
  const html = reasonRows({parts: [], kinds: [], imp: [['家族', 1, '終わった<舞台>', '家族の描写が好きだった。'], ['恋愛', -1, '', '恋愛は苦手']]}, new Map());
  assert.match(html, /<span class="net">感想<\/span><b>家族<\/b><span class="n">（『終わった&lt;舞台&gt;』の感想「家族の描写が好きだった。」）<\/span>/);
  assert.match(html, /<b>恋愛<\/b><span class="n">（感想「恋愛は苦手」で合わないと書いた）/);
});
