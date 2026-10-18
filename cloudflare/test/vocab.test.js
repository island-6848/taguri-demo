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
