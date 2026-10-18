// 題材の語彙表（src/vocab/concepts.json）: お気に入りの題材が下位・関連の言葉にも当たること。
import {DatabaseSync} from 'node:sqlite';
import {readFileSync, readdirSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {themeExpansion, vocabProblems} from '../src/vocab.js';
import {declaredLabels} from '../src/screens/lists.js';
import {d1Access, seedsFromFavourites, THEME_AXIS} from '../src/recommend.js';

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
  assert.deepEqual([...themeExpansion('家族').narrow], []);
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
  assert.deepEqual(seeds.map(s => s.stage_id).sort(), ['1', '2']);
});
