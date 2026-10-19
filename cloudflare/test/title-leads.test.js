// 題名の頭に「舞台」「ミュージカル」などが付いた過去の公演も、その後ろの題名で見つかる（起案者の指摘 2026-10-19「『銀河鉄道の父』を
// 探そうとしたら『舞台 銀河鉄道の父』で登録されてるらしくて参照できなかった。せめて公演タイトルの検索だけでもどうにかできない？」）
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {setup, step, signIn} from './screens/harness.js';
import {titleKey, titlePrefixes, prefixWhere} from '../src/stage-search.js';

test('titlePrefixes: the query, without a leading form word, and with each form word in front', () => {
  const ks = titlePrefixes(titleKey('銀河鉄道の父'));
  assert.ok(ks.includes('銀河鉄道の父') && ks.includes('舞台銀河鉄道の父') && ks.includes('ミュージカル銀河鉄道の父'));
  assert.ok(titlePrefixes(titleKey('ミュージカル エリザベート')).includes('エリザベート'));
  // 頭の語だけを打ったときは外さない（「舞台」で「舞台…」を探せる）
  assert.ok(!titlePrefixes(titleKey('舞台')).includes(''));
  // D1 の 1 回の問い合わせに渡せる数（100）に、ほかの条件と合わせて収まる
  assert.ok(prefixWhere(ks).args.length <= 60);
});

test('「舞台 銀河鉄道の父」 is found by 「銀河鉄道の父」 in the suggestions and on 探す', async () => {
  const {env, sqlite} = setup();
  const a = await signIn(env);
  try {
    const ins = sqlite.prepare("INSERT INTO past_stage(stage_id,title,tkey,start,end,venue,grp,pref,people) VALUES(?,?,?,'2023-03-01','2023-03-10','劇場Z','劇団Q','東京都','[]')");
    ins.run('9101', '舞台 銀河鉄道の父', titleKey('舞台 銀河鉄道の父'));
    ins.run('9102', 'ミュージカル「銀河鉄道の父」', titleKey('ミュージカル「銀河鉄道の父」'));
    ins.run('9103', '銀河の果て', titleKey('銀河の果て'));
    const got = (await step(env, a, {get: '/api/suggest?q=' + encodeURIComponent('銀河鉄道の父')})).body.rows;
    assert.deepEqual(got.map(r => r.title).sort(), ['ミュージカル「銀河鉄道の父」', '舞台 銀河鉄道の父']);
    const page = (await step(env, a, {get: '/api/screen/search?q=' + encodeURIComponent('銀河鉄道の父')})).body.body_html;
    assert.match(page, /舞台 銀河鉄道の父/);
    assert.doesNotMatch(page, /銀河の果て/);
  } finally { sqlite.close(); }
});

// 見つかった過去の公演は全部出す（起案者の指示 2026-10-19「新しい順から15件表示するのではなく、ちゃんと全件表示して」）
test('all past stages found are listed on 探す, not the newest 15', async () => {
  const {env, sqlite} = setup();
  const a = await signIn(env);
  try {
    const ins = sqlite.prepare("INSERT INTO past_stage(stage_id,title,tkey,start,end,venue,grp,pref,people) VALUES(?,?,?,?,?,'劇場Z',?,'東京都','[]')");
    for (let i = 0; i < 35; i++) {
      const d = `${2019 + (i % 6)}-${String(1 + Math.floor(i / 6)).padStart(2, '0')}-01`;   // どれも終わった公演（2019〜2024 年）
      ins.run(String(9300 + i), `星の旅 ${i}`, titleKey(`星の旅 ${i}`), d, d, `劇団${i}`);
    }
    // 1 ページ 5 件でページ送り（起案者の指示 2026-10-19「5 件ずつ表示し、ページ送りで最後までたどる」）
    const page = (await step(env, a, {get: '/api/screen/search?q=' + encodeURIComponent('星の旅')})).body.body_html;
    assert.equal((page.match(/class="pastrow"/g) || []).length, 5);
    assert.match(page, /過去の公演（2019 年〜） 35 件/);
    assert.match(page, /<span class="mp">1 \/ 7 ページ<\/span><a class="mpage" href="\/search\?t=__TAGURI_TOKEN__&amp;q=[^"]*&amp;pp=2#past-hits">次の 5 件 →<\/a>/);
    const p2 = (await step(env, a, {get: '/api/screen/search?q=' + encodeURIComponent('星の旅') + '&pp=7'})).body.body_html;
    assert.equal((p2.match(/class="pastrow"/g) || []).length, 5);
  } finally { sqlite.close(); }
});
