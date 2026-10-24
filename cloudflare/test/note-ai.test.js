// 感想の AI 読み取り（起案者の指示 2026-10-21「感想を送信することにチェックした場合のみ可能（設定画面に同意非同意つくって）」
// 「haikuにしたい」、note-ai.js）。同意した人の感想だけを送り、送る中身は本文と候補の言葉だけ
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {setup, signIn, step} from './screens/harness.js';
import {runNoteAi, parseBatch, buildBatch, noteHash, NOTE_AI_MODEL, PROMPT_VER} from '../src/note-ai.js';
import {impressionAdjust} from '../src/impression.js';

const SID = '9701';
function world() {
  const {env, sqlite} = setup();
  sqlite.prepare("INSERT INTO rec_people(ver,stage_id,people) VALUES((SELECT v FROM rec_meta WHERE k='current'),?,?)")
    .run(SID, JSON.stringify([['#題材', '家族'], ['#形式', '会話劇'], ['出演', '山田太郎'], ['#題材', '戦争']]));
  env.__sqlite = sqlite;
  return {env, sqlite};
}
async function noteFor(env, a, title, note) {
  const k = (await step(env, a, {post: '/api/add_work', body: {title, date: '2026-09-01'}})).body.work_key;
  await step(env, a, {post: '/api/note', body: {work_key: k, note_impression: note}});
  env.__sqlite.prepare('UPDATE works SET stage_id=? WHERE work_key=?').run(SID, k);   // 公演に結び付ける（試験の索引には無い番号）
  return k;
}
// 作り物の Anthropic: 受け取った問い合わせを控え、決めた答えを返す
const fake = reply => { const calls = []; return {calls, messages: {create: async req => { calls.push(req); return {stop_reason: 'end_turn', usage: {input_tokens: 120, output_tokens: 9}, content: [{type: 'text', text: reply(req)}]}; }}}; };

test('parseBatch: 番号と符号だけを読み、候補に無い番号や崩れた行は使わない', () => {
  const items = [{cands: ['家族', '戦争']}, {cands: ['会話劇']}, {cands: ['家族']}];
  assert.deepEqual(parseBatch('1:1+ 2-\n2:\n3:5+', items), [[['家族', 1], ['戦争', -1]], [], null]);
  assert.deepEqual(parseBatch('2：1＋', items), [null, [['会話劇', 1]], null]);
  assert.equal(buildBatch([{cands: ['家族', '戦争'], body: '泣いた。\n長い'}]), '1|候補:1家族 2戦争|感想:泣いた。 長い');
});

test('同意した人の感想だけを Haiku 5.5 に送り、本文と候補の言葉のほかは送らない。同じ感想は 2 度送らない', async () => {
  const {env, sqlite} = world();
  try {
    const yes = await signIn(env), no = await signIn(env);
    const k = await noteFor(env, yes, '同意した人の公演', '家族の話に弱いので泣いた。戦争の場面は長く感じた');
    await noteFor(env, no, '同意しない人の公演', '家族の話が良かった。とても良かったです');
    // 既定は同意していない: 何も送らない
    const f0 = fake(() => '1:1+');
    assert.equal((await runNoteAi(env, {client: f0})).sent, 0);
    assert.equal(f0.calls.length, 0);
    // 設定の画面に同意・非同意の欄がある
    const page = (await step(env, yes, {get: '/api/screen/settings'})).body.body_html;
    assert.match(page, /感想の AI 読み取り[\s\S]*?いまは同意していない[\s\S]*?name="note_ai" value="0" checked/);
    assert.equal((await step(env, yes, {post: '/api/note_ai', body: {on: true}})).status, 200);
    const f = fake(() => '1:1+ 3-');
    const r = await runNoteAi(env, {client: f, now: Date.parse('2026-10-22T18:41:00Z')});
    assert.deepEqual([r.sent, r.saved], [1, 1]);
    const req = f.calls[0];
    assert.equal(req.model, NOTE_AI_MODEL);
    assert.deepEqual(req.thinking, {type: 'disabled'});
    assert.equal(req.messages.length, 1);
    const sent = req.messages[0].content;
    // 候補は種類の言葉（#題材・#形式）だけで、出演者は入らない。題名・作品の番号・利用者の番号も入らない
    assert.equal(sent, '1|候補:1家族 2会話劇 3戦争|感想:家族の話に弱いので泣いた。戦争の場面は長く感じた');
    assert.doesNotMatch(sent, /同意しない人|同意した人の公演|山田太郎/);
    const row = sqlite.prepare('SELECT * FROM note_ai').get();
    assert.deepEqual([row.work_key, row.status, JSON.parse(row.feats), row.model, row.prompt_ver, row.note_hash],
      [k, 'ok', [['家族', 1], ['戦争', -1]], NOTE_AI_MODEL, PROMPT_VER, noteHash('家族の話に弱いので泣いた。戦争の場面は長く感じた')]);
    assert.equal(sqlite.prepare("SELECT n FROM usage WHERE k='note_ai_tokens:2026-10'").get().n, 129);
    // 同じ感想は送らない。書き直すと送る
    const f2 = fake(() => '1:');
    assert.equal((await runNoteAi(env, {client: f2})).sent, 0);
    await step(env, yes, {post: '/api/note', body: {work_key: k, note_impression: '戦争の場面がつらかった'}});
    sqlite.prepare("UPDATE note_ai SET analyzed_at='2000-01-01'").run();   // 書き直しの時刻が読み取りより後になるように
    assert.equal((await runNoteAi(env, {client: f2})).sent, 1);
    assert.equal(sqlite.prepare('SELECT status FROM note_ai').get().status, 'none');
    // 同意をやめると、読み取った結果を消し、もう送らない
    await step(env, yes, {post: '/api/note_ai', body: {on: false}});
    assert.equal(sqlite.prepare('SELECT count(*) n FROM note_ai').get().n, 0);
    const f3 = fake(() => '1:1+');
    assert.equal((await runNoteAi(env, {client: f3})).sent, 0);
  } finally { sqlite.close(); }
});

test('鍵が無ければ送らない。AI が断った感想は読み直さない。月の上限を越えたら送らない', async () => {
  const {env, sqlite} = world();
  try {
    const a = await signIn(env);
    await noteFor(env, a, '公演', '家族の話に弱いので泣いた');
    await step(env, a, {post: '/api/note_ai', body: {on: true}});
    assert.equal((await runNoteAi(env)).stopped, 'no-key');
    const refuse = {calls: [], messages: {create: async () => ({stop_reason: 'refusal', usage: {input_tokens: 5, output_tokens: 0}, content: []})}};
    await runNoteAi(env, {client: refuse});
    assert.equal(sqlite.prepare('SELECT status FROM note_ai').get().status, 'refused');
    sqlite.prepare('DELETE FROM note_ai').run();
    sqlite.prepare("INSERT INTO usage(k,n) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET n=excluded.n").run(`note_ai_tokens:${new Date().toISOString().slice(0, 7)}`, 9_000_000);
    const f = fake(() => '1:1+');
    assert.equal((await runNoteAi(env, {client: f})).stopped, 'cap');
    assert.equal(f.calls.length, 0);
  } finally { sqlite.close(); }
});

test('impressionAdjust: 感想の文が読み取った時と同じなら AI の結果を使い、書き直した後は決まりで読む', async () => {
  const note = '家族の話は正直つまらなかった';   // 決まりでは「家族」に低い点が付かない言い回しでも、AI の読みを使う
  const rated = [{key: 'w1', title: 'A', date: '2026-09-01', note, people: [['#題材', '家族']]}];
  const postingsFor = async () => new Map();
  const ai = new Map([['w1', {hash: noteHash(note), feats: [['家族', -1]]}]]);
  const withAi = await impressionAdjust({postingsFor}, rated, ['#題材'], ai);
  assert.equal(withAi.profile.get('家族').evidence[0].value, -1);
  const stale = new Map([['w1', {hash: noteHash('前の感想'), feats: [['家族', 1]]}]]);
  const r = await impressionAdjust({postingsFor}, rated, ['#題材'], stale);
  assert.ok(!r || !r.profile.get('家族') || r.profile.get('家族').evidence[0].value !== 1);
});
