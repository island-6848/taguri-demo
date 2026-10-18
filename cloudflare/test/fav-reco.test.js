// お気に入りだけを登録した人のおすすめ（起案者の問い 2026-10-18「好きな俳優・劇団・作品を『お気に入り』に登録すると
// おすすめが出る、って書いてあるのに、何もでないときがある。なぜ？」、fix-fav-only-no-reco）と、お気に入りから広げる
// 関わりのある人の度合い（同じ日「共演者＞演出＞脚本＞＞＞翻訳＞主催＞美術・照明・音響・映像・衣裳・振付くらいだけでいい」、
// dec-fav-spread-roles）、効かせ方の初めの設定（同じ日、dec-weight-defaults）。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {setup, step, signIn} from './screens/harness.js';
import {personValues, scoreFromIndex, seedsFromFavourites, FAV_SPREAD_W} from '../src/recommend.js';
import {multipliersOf, tunedWeights, defaultStep, ROLE_GROUPS} from '../src/screens/weights.js';

const here = p => new URL(p, import.meta.url).pathname;
const FIXTURE = JSON.parse(execFileSync('python3', [here('./screens/recommend_fixture.py')], {encoding: 'utf8', maxBuffer: 64 * 1024 * 1024}));
async function withIndex() {
  const {env, sqlite} = setup();
  for (const s of FIXTURE.sql) sqlite.exec(s);
  return {env, sqlite};
}
async function favOnly(kind, name) {
  const {env, sqlite} = await withIndex();
  const a = await signIn(env);
  try {
    assert.equal((await step(env, a, {post: '/api/favourite', body: {action: 'add', kind, name}})).status, 200);
    return (await step(env, a, {get: '/api/screen/recommend'})).body;
  } finally { sqlite.close(); }
}

// 評価・興味ありが 1 件も無くても、お気に入りの公演（102 舞台ふたつめ）の共演者 俳優乙 の別の公演（101）が出る。
// 理由には、登録していない人を「好きな」とは書かず、登録した名前を書く
test('a favourite alone recommends a show of a co-worker, and the reason names the favourite', async () => {
  const got = await favOnly('人', '作家丁');
  assert.match(got.body_html, /<h1>今週のあなたへのおすすめ 1 件<\/h1>/);
  assert.match(got.body_html, /data-stage="101"/);
  assert.match(got.body_html, /出演 <b>俳優乙<\/b><span class="n">（お気に入りの作家丁と同じ公演に関わる人：『舞台ふたつめ』）<\/span>/);
  assert.doesNotMatch(got.body_html, /好きな俳優乙|おすすめを出すためのワンポイント/);
});

// 原因 1: 名前を空白入りで登録すると、お気に入りの一覧（空白を詰めて本文で当てる）には公演が出るのに、推薦の種（索引を
// 名前そのままで引く）は 0 件で、おすすめも 0 件だった。いまは同じ名前として引き、一覧に出る公演も種にする
test('a favourite written with a space (作家 丁) still seeds the recommendations', async () => {
  for (const name of ['作家 丁', '作家　丁']) {
    const got = await favOnly('人', name);
    assert.equal(got.diag.favourite_seeds, 1, name);
    assert.match(got.body_html, /data-stage="101"/, name);
    assert.match(got.body_html, new RegExp(`お気に入りの${name}と同じ公演に関わる人`), name);
    // 登録した本人（索引では「作家丁」）は理由に出さない
    assert.doesNotMatch(got.body_html, /<b>作家丁<\/b>/, name);
  }
});

// 劇団・作品で登録しても、理由に登録した名前を書く
test('a troupe or a work as the favourite is named in the reason', async () => {
  assert.match((await favOnly('団体', '劇団乙')).body_html, /（お気に入りの劇団乙と同じ公演に関わる人：『舞台ふたつめ』）/);
  assert.match((await favOnly('作品', '舞台ふたつめ')).body_html, /（お気に入りの舞台ふたつめと同じ公演に関わる人：『舞台ふたつめ』）/);
});

// 直せないもの（案内の文の限界）: 登録した人の公演の共演者・作り手に、まだ始まっていない別の公演が無いと 0 件のまま。
// 俳優甲の公演は 101（本人の公演なのでお気に入りの一覧に出る）と 103（終わった）、共演者 俳優乙 の別の公演 102 はもう始まっている
test('nothing to recommend when every co-worker\'s other show is the favourite\'s own, over, or already running', async () => {
  const got = await favOnly('人', '俳優甲');
  assert.equal(got.diag.favourite_seeds, 2);
  assert.match(got.body_html, /<h1>今週のあなたへのおすすめはありません<\/h1>/);
  // お気に入りがあるのに 0 件のときだけ、一文添える（起案者の答え 2026-10-18「C」）
  assert.match(got.body_html, /<p class="rcount favnone">お気に入りに登録した名前と関わりのある人の、これから観られる公演はまだ見つかっていません。/);
});

test('people of a favourite\'s show count by role: 出演 > 演出 > 脚本 > 翻訳 > 主催 > 美術…; 制作・宣伝・その他 not at all', () => {
  const roles = ['出演', '演出', '脚本', '翻訳', '主催', '照明', '制作', '宣伝', '舞台監督', 'スタッフ', '作曲'];
  const seed = {stage_id: 's', people: [...roles.map(r => [r, r + 'の人']), ['#形式', 'ミュージカル'], ['出演', '推し']]};
  const v = personValues([], [seed], new Set(['推し']));
  const val = r => (v.get(r + '\u0000' + r + 'の人') || [0, 0])[1];
  for (let i = 1; i < 6; i++) assert.ok(val(roles[i - 1]) > val(roles[i]), `${roles[i - 1]} > ${roles[i]}`);
  for (const r of ['制作', '宣伝', '舞台監督', 'スタッフ']) assert.equal(v.has(r + '\u0000' + r + 'の人'), false, r);
  // 作曲・音楽は美術などと同じ重みで広げる（起案者の答え 2026-10-18「作曲・音楽を広げる元に入れて」）
  assert.ok(Math.abs(val('作曲') / val('出演') - 0.1) < 1e-12);
  // 値は重みの比（分母は同じ）。公演の種類は人ではないので 1 のまま
  assert.ok(Math.abs(val('演出') / val('出演') - FAV_SPREAD_W['演出']) < 1e-12);
  assert.ok(Math.abs(val('照明') / val('出演') - 0.1) < 1e-12);
  assert.ok(Math.abs(v.get('#形式\u0000ミュージカル')[1] - val('出演')) < 1e-12);
  assert.equal(v.has('出演\u0000推し'), false);
});

// 原因 2（「好きな諸鍛冶裕太」）: お気に入りの公演の共演者を「好きな人」として、さらに 1 段広げていた（2 段先の人）
test('one step out starts from people the user rated or was interested in, not from a favourite\'s co-workers', async () => {
  // Q は S2 に、S2 で組む Y は S4 にも出る。S4 は Q からさらに 1 段先
  const CREDITS = [['出演', 'Q', 'S2', 1, 'cast'], ['出演', 'Y', 'S2', 1, 'cast'], ['出演', 'Y', 'S4', 1, 'cast']];
  const access = {
    postingsFor: async keys => { const want = new Set(keys.map(k => k.join('\u0000'))); return CREDITS.filter(c => want.has(c[0] + '\u0000' + c[1])); },
    stagesFor: async ids => new Map(ids.map(id => [id, {start: '2026-12-01', end: '2026-12-10', tour: ''}])),
  };
  const peopleFor = async ids => new Map(ids.map(id => [id, CREDITS.filter(c => c[2] === id).map(c => [c[0], c[1]])]));
  const seeds = [{stage_id: 'F', people: [['出演', '推し'], ['出演', 'Q']]}];
  const got = await scoreFromIndex({...access, rated: [], today: '2026-10-15', seeds, skip: new Set(['推し']), expand: {peopleFor}});
  assert.deepEqual(got.map(c => c.stage_id), ['S2']);
  assert.ok(got.every(c => !c.via), JSON.stringify(got));
  // 興味ありを押した公演の人からは、これまでどおり広げる
  const liked = [{stage_id: 'L', people: [['出演', 'Q']]}];
  const wide = await scoreFromIndex({...access, rated: [], today: '2026-10-15', liked, expand: {peopleFor}});
  assert.deepEqual(wide.map(c => c.stage_id), ['S2', 'S4']);
  assert.deepEqual(wide[1].via, [['出演\tY', 'Q']]);
});

test('効かせ方の初めの設定: 出演者・作品の内容は少し強く、制作・宣伝・その他の役職はあまり効かせない、ほかはふつう', () => {
  const w = Object.fromEntries(ROLE_GROUPS.map(([k]) => [k, defaultStep(k)]));
  assert.deepEqual(w, {cast: 'strong', author: 'mid', craft: 'mid', stage: 'mid', produce: 'weak', other: 'weak', theme: 'strong'});
  assert.deepEqual(multipliersOf(w), {cast: 2.0, produce: 0.5, other: 0.5, theme: 2.0});
  assert.equal(tunedWeights(w), false);
  assert.equal(tunedWeights({...w, cast: 'mid'}), true);
  // Python の app と同じ既定
  const py = JSON.parse(execFileSync('python3', ['-c', `
import json, sys
sys.path[:0] = ['../tools/taguri', '../tools/review']
import app as APP
print(json.dumps({k: APP.default_step(k) for k, _l, _r in APP.ROLE_GROUPS}))`], {encoding: 'utf8', stdio: ['pipe', 'pipe', 'ignore']}));
  assert.deepEqual(py, w);
});

// 題材を語彙表で広げた言葉（「科学」→ ロボット …、PR #210）で当たった公演も、理由には登録した題材の語を書く
test('a subject widened by the vocabulary is named by the registered subject', async () => {
  // 語彙表で広げた言葉は stagesByWords（重さつき、PR #211）で引く。広げた言葉で当たった公演も、理由には登録した題材を書く
  const calls = [];
  const access = {
    postingsFor: async () => [],
    peopleFor: async ids => new Map(ids.map(id => [id, [['出演', '俳優' + id]]])),
    stagesMatching: async (groups, works, subjects, exact, labels) => {
      calls.push({subjects});
      labels.set('S2', new Set(['科学']));
      return ['S2'];
    },
    stagesByWords: async (weights, labels) => {
      calls.push({words: [...weights.keys()]});
      labels.set('S1', new Set(['ロボット']));
      return new Map([['S1', 0.3]]);
    },
  };
  const got = await seedsFromFavourites(access, [{name: '科学', kind: '題材'}]);
  assert.ok(calls[0].subjects.includes('科学'));
  assert.ok(calls[1].words.includes('ロボット'), JSON.stringify(calls[1].words));
  assert.deepEqual(got.seeds.map(s => [s.stage_id, s.fav, s.w ?? 1]), [['S2', ['科学'], 1], ['S1', ['科学'], 0.3]]);
});
