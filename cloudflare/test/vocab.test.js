// 題材の語彙表（src/vocab/concepts.json）: お気に入りの題材が下位・関連の言葉にも当たること。
import {DatabaseSync} from 'node:sqlite';
import {readFileSync, readdirSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {themeExpansion, vocabProblems} from '../src/vocab.js';
import {declaredLabels} from '../src/screens/lists.js';
import {d1Access, seedsFromFavourites, personValues, THEME_AXIS} from '../src/recommend.js';

test('語彙表に、存在しない上位・関連や、上位の輪が無い', () => {
  assert.deepEqual(vocabProblems(), []);
});

test('「科学」は SF とその下位に広がり、近未来は関連にだけ入る', () => {
  const {narrow, related} = themeExpansion('科学');
  for (const w of ['sf', 'sfホラー', '宇宙', '宇宙人', 'ロボット', 'ai', 'タイムスリップ', 'ディストピア', '生命科学']) assert.ok(narrow.has(w), w);
  assert.ok(!narrow.has('科学'), '登録した言葉そのものは含めない');
  assert.ok(!narrow.has('近未来') && related.has('近未来') && related.has('未来'));
  assert.ok(related.has('超能力'));
  // 孫（終末・ディストピア）の関連（戦争）まではたどらない
  assert.ok(!related.has('戦争') && !related.has('戦後'));
  // 下位から上には広げない
  const sf = themeExpansion('ＳＦ');
  assert.ok(sf.narrow.has('宇宙') && !sf.narrow.has('科学') && !sf.narrow.has('生命科学'));
  assert.deepEqual([...themeExpansion('サッカー').narrow], []);
});

test('離れるほど弱い: 子 0.6・孫 0.35・関連 0.3、別の道で着いたら近いほう', () => {
  const {weights} = themeExpansion('科学');
  assert.equal(weights.get('sf'), 0.6);
  assert.equal(weights.get('sfホラー'), 0.6, 'SF の言葉は SF と同じ段');
  assert.equal(weights.get('宇宙'), 0.35);
  assert.equal(weights.get('近未来'), 0.3);
  assert.ok(Math.abs(weights.get('サイエンス') - 1) < 1e-9, '同義語は登録した言葉と同じ');
  // 上位が二つある概念（ホームコメディ ⊂ 喜劇・家族）は、どちらから広げても子
  assert.equal(themeExpansion('家族').weights.get('ホームコメディ'), 0.6);
  assert.equal(themeExpansion('コメディ').weights.get('ホームコメディ'), 0.6);
  assert.ok(themeExpansion('ダンス').narrow.has('古典舞踊') && themeExpansion('伝統芸能').narrow.has('古典舞踊'));
});

test('概念の言葉を登録したときは、同じ概念の言葉を仲間（関連）として弱く扱い、一覧には出さない', () => {
  const x = themeExpansion('宇宙人');
  assert.deepEqual([...x.narrow], []);
  assert.ok(x.related.has('宇宙船'));
  assert.equal(x.weights.get('宇宙船'), 0.3);
  assert.deepEqual(declaredLabels(card(['宇宙船']), {'題材': ['宇宙人']}), []);
});

const card = ws => ({gnz: '', blob: '', ws: ws.join('\n'), synz: ''});

test('お気に入り一覧: 広げた言葉は #題材 と丸ごと一致したときだけ当たり、関連は当たらない', () => {
  const declared = {'題材': ['科学']};
  assert.deepEqual(declaredLabels(card(['家族', 'sf']), declared), ['題材「科学」']);
  assert.deepEqual(declaredLabels(card(['宇宙人']), declared), ['題材「科学」']);
  assert.deepEqual(declaredLabels(card(['コーラスグループ']), declared), [], '「ループ」の部分一致で当てない');
  assert.deepEqual(declaredLabels(card(['近未来', '家族']), declared), [], '近未来は関連なので一覧には出さない');
  // これまでの当て方（言葉の一部）は変えない
  assert.deepEqual(declaredLabels(card(['科学史']), declared), ['題材「科学」']);
});

test('推薦の種: 「科学」で SF と近未来の公演が拾われ、関係の無い公演は拾われない', async () => {
  const sqlite = new DatabaseSync(':memory:');
  for (const f of readdirSync(new URL('../migrations/', import.meta.url)).filter(n => n.endsWith('.sql')).sort())
    sqlite.exec(readFileSync(new URL(`../migrations/${f}`, import.meta.url), 'utf8'));
  const ins = sqlite.prepare('INSERT INTO rec_credit (ver,role,person,stage_id,role_w,role_group) VALUES (?,?,?,?,?,?)');
  const ppl = sqlite.prepare('INSERT INTO rec_people (ver,stage_id,people) VALUES (?,?,?)');
  for (const [sid, word] of [['1', 'sf'], ['2', '近未来'], ['3', 'コーラスグループ'], ['4', '家族']]) {
    ins.run('v', THEME_AXIS, word, sid, 1, 'theme');
    ppl.run('v', sid, JSON.stringify([[THEME_AXIS, word]]));
  }
  const wrap = (sql, args = []) => ({bind(...v) { return wrap(sql, v); }, async all() { return {results: sqlite.prepare(sql).all(...args)}; }});
  const access = d1Access({prepare: sql => wrap(sql)}, 'v');
  const {seeds} = await seedsFromFavourites(access, [{kind: '題材', name: '科学'}]);
  assert.deepEqual(seeds.map(s => [s.stage_id, s.w]), [['1', 0.6], ['2', 0.3]], '重い順、重さ付き');
  // 弱い種ほど、そこにいる人の値の上がり方が小さい
  const v = personValues([], seeds);
  assert.ok(v.get(THEME_AXIS + '\u0000sf')[1] > v.get(THEME_AXIS + '\u0000近未来')[1]);
  const full = personValues([], [{...seeds[0], w: undefined}]);
  assert.ok(full.get(THEME_AXIS + '\u0000sf')[1] > v.get(THEME_AXIS + '\u0000sf')[1]);
});

// 下から上への積み上げ（起案者の指示 2026-10-18「仕組みの案の 1,2 どっちもやりたい」「それなら SF って出しちゃっていいよ」）
import {rolledThemeWords, ROLLUP_MIN_BRANCHES} from '../src/vocab.js';
import {scoreFromIndex} from '../src/recommend.js';

test('細かい好みが 3 つの枝にまたがると上位（SF）の好みになり、下の言葉へ広がる。枝が足りなければ広げない', () => {
  assert.equal(ROLLUP_MIN_BRANCHES, 3);
  const three = rolledThemeWords(new Map([['宇宙船', [1, 0.5]], ['ロボット', [1, 0.4]], ['タイムスリップ', [1, 0.3]]]));
  assert.equal(three.get('宇宙人')[0], 'SF', 'いちばん近い上位の名前');
  assert.ok(three.get('宇宙人')[2] > 0);
  assert.equal(three.get('生命科学')[0], '科学', 'SF の外は科学から');
  assert.ok(three.get('生命科学')[2] < three.get('宇宙人')[2], '遠いほど弱い');
  assert.ok(!three.has('宇宙船'), '自分の値を持つ言葉には広げない（細かい好みが勝つ）');
  assert.ok(!three.has('近未来'), '関連には広げない');
  const two = rolledThemeWords(new Map([['宇宙船', [1, 0.5]], ['ロボット', [1, 0.4]]]));
  assert.equal(two.size, 0);
  const oneBranch = rolledThemeWords(new Map([['宇宙船', [1, 0.5]], ['宇宙人', [1, 0.5]], ['火星', [1, 0.5]]]));
  assert.ok(!oneBranch.has('ロボット'), '同じ枝（宇宙もの）だけなら SF まで上げない');
  const talk = rolledThemeWords(new Map([['会話劇', [1, 0.5]], ['群像劇', [1, 0.4]], ['二人芝居', [1, 0.3]]]));
  assert.ok(!talk.has('朗読劇'), '軸の見出し（語り口）へは積み上げない');
  const down = rolledThemeWords(new Map([['宇宙船', [1, -0.5]], ['ロボット', [1, -0.4]], ['タイムスリップ', [1, -0.3]]]));
  assert.ok(down.get('宇宙人')[2] < 0, '苦手も同じ向きで積み上げる');
});

test('積み上げた上位の好みで、細かい言葉しか付いていない公演が上がり、理由に上位の名前が出る', async () => {
  const T = '#題材';
  const credits = [[T, '宇宙人', 'C1', 1, 'theme'], [T, '家族の秘密', 'C2', 1, 'theme']];
  const access = {
    postingsFor: async keys => { const want = new Set(keys.map(k => k.join('\u0000'))); return credits.filter(c => want.has(c[0] + '\u0000' + c[1])); },
    stagesFor: async ids => new Map(ids.map(id => [id, {start: '2026-12-01', end: '2026-12-10', tour: ''}])),
  };
  const rated = [['宇宙船', '◎'], ['ロボット', '◎'], ['タイムスリップ', '◎'], ['家族', '×'], ['恋愛', '×'], ['落語', '×']]
    .map(([w, v], i) => ({key: 'r' + i, verdict: v, people: [[T, w]], updated_at: String(i)}));
  const out = await scoreFromIndex({...access, rated, today: '2026-10-18'});
  const c1 = out.find(c => c.stage_id === 'C1');
  assert.ok(c1, 'SF の下の「宇宙人」の公演が出る');
  assert.deepEqual(c1.kinds.map(k => k.slice(1, 3)), [[T, 'SF']]);
  const off = await scoreFromIndex({...access, rated, today: '2026-10-18', ablate: {rollup: true}});
  assert.ok(!off.find(c => c.stage_id === 'C1'), '積み上げを外すと出ない');
});
