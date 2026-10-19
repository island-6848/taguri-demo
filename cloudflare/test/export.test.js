// #192: 利用者向けの書き出し（/export.json）に、本人の私的な記録が欠けずに入ること。
// 手入力のクレジット・まとめた記録・観た回のメモ・効かせ方・お気に入りの表・設定も入れ、
// ログインの秘密（セッション・復旧コード・パスキー）は入れない。ほかの人の行も入れない
import {test} from 'node:test';
import assert from 'node:assert/strict';
import worker from '../src/worker.js';
import {setup, signIn, step} from './screens/harness.js';

const ORIGIN = 'https://taguri.example';

async function exported(env, cookie) {
  const res = await worker.fetch(new Request(`${ORIGIN}/export.json`, {headers: {cookie}}), env);
  assert.equal(res.status, 200);
  return {text: await res.clone().text(), out: await res.json()};
}

test('the export holds every private table of the user, with a schema version, and no sign-in secrets', async () => {
  const {env, sqlite} = setup();
  try {
    const a = await signIn(env);
    const uidA = sqlite.prepare('SELECT id FROM users').get().id;
    const b = await signIn(env);
    const uidB = sqlite.prepare('SELECT id FROM users WHERE id<>?').get(uidA).id;
    for (const [uid, tag] of [[uidA, 'A'], [uidB, 'B']]) {
      sqlite.prepare("INSERT INTO hand_credits(user_id,work_key,fields,poster,updated_at) VALUES(?,?,?,'', '2026-10-01')").run(uid, `w${tag}`, JSON.stringify({出演: [`手入力の俳優${tag}`]}));
      sqlite.prepare("INSERT INTO merges(user_id,work_key,into_key,updated_at) VALUES(?,?,?,'2026-10-01')").run(uid, `まとめ元${tag}`, `まとめ先${tag}`);
      sqlite.prepare("INSERT INTO visit_note(user_id,uid,note,updated_at) VALUES(?,?,?,'2026-10-01')").run(uid, `v${tag}`, `観た回のメモ${tag}`);
      sqlite.prepare("INSERT INTO rank_weight(user_id,grp,step,updated_at) VALUES(?,?,3,'2026-10-01')").run(uid, `効かせ方${tag}`);
      sqlite.prepare('INSERT INTO favourites(user_id,name,kind) VALUES(?,?,?)').run(uid, `表のお気に入り${tag}`, '人');
      sqlite.prepare("INSERT INTO app_setting(user_id,key,value,updated_at) VALUES(?,'rating_scale',?,'2026-10-01')").run(uid, `"scale${tag}"`);
      sqlite.prepare("INSERT INTO search_request(user_id,qkey,query,source,created_at) VALUES(?,?,?,'web','2026-10-01')").run(uid, `q${tag}`, `探した言葉${tag}`);
    }
    // 画面から足したお気に入り（app_setting の declared）
    assert.equal((await step(env, a, {post: '/api/favourite', body: {action: 'add', kind: '人', name: '画面のお気に入りA'}})).status, 200);
    const {text, out} = await exported(env, a);
    assert.equal(out.schema_version, 2);
    assert.match(out.exported_at, /^\d{4}-\d{2}-\d{2}T/);
    // これまでの鍵はそのまま（ほかの道具で読んでいる人の書き出しを壊さない）
    for (const k of ['works', 'ratings', 'attendance', 'reaction', 'ticket', 'presented', 'splits', 'excluded', 'missed', 'declared']) assert.ok(k in out, k);
    assert.ok(!('rec_shown' in out) && !('viewed' in out), 'measurement logs are not exported');
    assert.equal(out.hand_credits[0].work_key, 'wA');
    assert.deepEqual(out.merges.map(r => r.into_key), ['まとめ先A']);
    assert.deepEqual(out.visit_note.map(r => r.note), ['観た回のメモA']);
    assert.deepEqual(out.rank_weight.map(r => [r.grp, String(r.step)]), [['効かせ方A', '3']]);
    assert.deepEqual(out.favourites.map(r => r.name), ['表のお気に入りA']);
    assert.ok(out.settings.some(r => r.key === 'rating_scale' && r.value === '"scaleA"'));
    assert.deepEqual(out.search_request.map(r => r.query), ['探した言葉A']);
    // お気に入りは、画面の控えと表の両方を合わせて declared に（loadDeclared と同じ）
    assert.deepEqual(out.declared['人'].sort(), ['画面のお気に入りA', '表のお気に入りA'].sort());
    // ほかの人の行・ログインの秘密は入らない
    assert.doesNotMatch(text, /B"|俳優B|メモB|効かせ方B|お気に入りB|scaleB|言葉B/);
    for (const k of ['sessions', 'passkeys', 'webauthn_challenges', 'users', 'recovery_hash', 'firebase_uid']) assert.ok(!(k in out), k);
    const secrets = [...sqlite.prepare('SELECT hash FROM sessions').all().map(r => r.hash), ...sqlite.prepare('SELECT recovery_hash FROM users').all().map(r => r.recovery_hash)];
    for (const s of secrets) assert.ok(!text.includes(s), 'a sign-in secret is in the export');
    assert.ok(!text.includes(a.split('=')[1]));
    // 設定の「書き出す」の欄も、新しく入れたものを数える（JSON の版や日時は数えない）
    const html = (await step(env, a, {get: '/api/screen/settings'})).body.body_html;
    assert.match(html, /<span class="xk">hand_credits<\/span>/);
    assert.doesNotMatch(html, /<span class="xk">(schema_version|exported_at)<\/span>/);
  } finally { sqlite.close(); }
});
