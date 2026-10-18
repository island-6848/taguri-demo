// 興味ありの配り方（起案者の指示 2026-10-15「1+2+3まとめて入れて」、impl-interest-split）。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {interestShares, interestContrast, personValues, INTEREST_PEOPLE_SHARE} from '../src/recommend.js';

const K = (r, p) => r + '\u0000' + p;
const sum = m => [...m.values()].reduce((a, b) => a + b, 0);
const close = (a, b) => assert.ok(Math.abs(a - b) < 1e-9, `${a} != ${b}`);

test('(1) one stage gives one rating\'s worth, split over its people and kinds', () => {
  const s = {people: [['出演', 'A'], ['出演', 'B'], ['出演', 'C'], ['演出', 'D'], ['#原作', 'オリジナル']]};
  const m = interestShares(s, new Map());
  close(sum(m), 1);
  close(m.get(K('出演', 'A')), INTEREST_PEOPLE_SHARE / 4);
  close(m.get(K('#原作', 'オリジナル')), 1 - INTEREST_PEOPLE_SHARE);
  // A big cast spreads thin: an ensemble member of a 40-person cast gets a fortieth of the people's half.
  const big = {people: Array.from({length: 40}, (_, i) => ['出演', `P${i}`])};
  close(interestShares(big, new Map()).get(K('出演', 'P7')), 1 / 40);
});

test('(1) only what several 興味あり share adds up', () => {
  const a = {people: [['出演', '共通'], ['出演', 'X1'], ['出演', 'X2']]}, b = {people: [['出演', '共通'], ['出演', 'Y1'], ['出演', 'Y2']]};
  const v = personValues([], [], new Set(), [a, b]);
  assert.ok(v.get(K('出演', '共通'))[1] > 1.7 * v.get(K('出演', 'X1'))[1]);
});

test('(2) a person already liked gets more of the stage', () => {
  const s = {people: [['出演', '好き'], ['出演', '他']]};
  const m = interestShares(s, new Map([[K('出演', '好き'), [2, 0.5]]]));
  assert.ok(m.get(K('出演', '好き')) > 2 * m.get(K('出演', '他')));
  close(sum(m), 1);
  // A negative value does not take a share away below the even split.
  const n = interestShares(s, new Map([[K('出演', '好き'), [2, -0.5]]]));
  close(n.get(K('出演', '好き')), 0.5);
});

test('(3) what is also in 興味なし weighs less; the rest keeps its share', () => {
  const liked = [{people: [['出演', 'どちらも'], ['出演', 'ありだけ']]}];
  const disliked = [{people: [['出演', 'どちらも'], ['出演', 'なしだけ']]}];
  const c = interestContrast(liked, disliked);
  assert.deepEqual(c.get(K('出演', 'どちらも')), [1, 1]);
  const m = interestShares(liked[0], new Map(), c);
  close(m.get(K('出演', 'ありだけ')), 1 / 2);
  close(m.get(K('出演', 'どちらも')), 1 / 4);
});

// #109: the weakening was applied before the shares were renormalised, so a stage whose keys are all
// in 興味なし in the same proportion (one person and one form, say) lost nothing however many 興味なし came.
test('(3) 興味なし on the same people and kinds weakens them, however few keys the stage has', () => {
  const liked = [{people: [['出演', 'A'], ['#形式', 'X']]}];
  const same = () => ({people: [['出演', 'A'], ['#形式', 'X']]});
  const val = (dis, k) => personValues([], [], new Set(), liked, dis).get(k)[1];
  for (const k of [K('出演', 'A'), K('#形式', 'X')]) {
    const v0 = val([], k), v1 = val([same()], k), v20 = val(Array.from({length: 20}, same), k);
    assert.ok(v1 < v0 && v20 < v1, `${k}: ${v0} > ${v1} > ${v20}`);
    assert.ok(v20 < v0 / 10, '20 興味なし leave little of one 興味あり');
  }
  // Only one of the two shared: that one weakens, the other does not gain from it.
  const onlyA = [{people: [['出演', 'A'], ['#形式', 'Y']]}];
  close(val(onlyA, K('#形式', 'X')), val([], K('#形式', 'X')));
  assert.ok(val(onlyA, K('出演', 'A')) < val([], K('出演', 'A')));
  // A one-key stage too.
  const one = [{people: [['出演', 'A']]}];
  assert.ok(personValues([], [], new Set(), one, [{people: [['出演', 'A']]}]).get(K('出演', 'A'))[1]
    < personValues([], [], new Set(), one, []).get(K('出演', 'A'))[1]);
});

test('the optional note naming a person gives that person more', () => {
  const s = {note: '山田花子さんが出るから', people: [['出演', '山田花子'], ['出演', '他の人'], ['出演', '別の人']]};
  const m = interestShares(s, new Map());
  close(m.get(K('出演', '山田花子')), 5 / 7);
});

test('favourites are skipped, and seeds fade with ratings as before', () => {
  const s = {people: [['出演', 'お気に入り'], ['出演', '他']]};
  const m = interestShares(s, new Map(), new Map(), new Set(['お気に入り']));
  assert.deepEqual([...m.keys()], [K('出演', '他')]);
  const rated = Array.from({length: 9}, (_, i) => ({verdict: i % 2 ? '◎' : '×', people: [['出演', `R${i}`]]}));
  const few = personValues([], [], new Set(), [s]).get(K('出演', '他'))[1];
  const many = personValues(rated, [], new Set(), [s]).get(K('出演', '他'))[1];
  assert.ok(few > 3 * many);
});

// 役柄の重さ（起案者の指示 2026-10-15「単純に人数で割るのよくない。役柄の重要さで割るべき」）。
import {castImportance, LESSER_IMPORTANCE} from '../src/recommend.js';

test('トメ: the last name on its own line is a main role even after the ensemble; the last of the ensemble line is not', () => {
  const m = castImportance('主役一、脇役二\nアンサンブル：群甲、群乙、群丙\n重鎮四', ['主役一', '脇役二', '群甲', '群乙', '群丙', '重鎮四']);
  close(m.get('重鎮四'), 1);
  close(m.get('群丙'), LESSER_IMPORTANCE);
  const n = castImportance('主役一、脇役二\nアンサンブル：群甲、群乙、群丙', ['主役一', '脇役二', '群甲', '群乙', '群丙']);
  close(n.get('群丙'), LESSER_IMPORTANCE);
  // Two names only: no トメ.
  close(castImportance('アンサンブル：群甲\n重鎮', ['群甲', '重鎮']).get('重鎮'), LESSER_IMPORTANCE);
});

// 案 B（起案者 2026-10-15）: 役の格は 2 段だけ。書かれた順・トメは使わない。
test('cast: named parts are the main roles, all equal; the ensemble weighs less', () => {
  const text = 'ジャン・バルジャン：主役一\nジャベール：主演二\nファンテーヌ：助演三\n司教：重鎮四\nアンサンブル：群衆五、群衆六';
  const m = castImportance(text, ['群衆六', '助演三', '主役一', '主演二', '群衆五', '重鎮四', '載っていない']);
  for (const n of ['主役一', '主演二', '助演三', '重鎮四']) close(m.get(n), 1);
  for (const n of ['群衆五', '群衆六', '載っていない']) close(m.get(n), LESSER_IMPORTANCE);
});

test('cast without part names: the ensemble heading is the border; without one, everyone is equal', () => {
  const m = castImportance('甲野、乙野、丙野\nアンサンブル：丁野', ['甲野', '乙野', '丙野', '丁野']);
  for (const n of ['甲野', '乙野', '丙野']) close(m.get(n), 1);
  close(m.get('丁野'), LESSER_IMPORTANCE);
  const o = castImportance('出演：甲野\n乙野', ['甲野', '乙野']);
  close(o.get('甲野'), 1);
  close(o.get('乙野'), 1);
});

test('a 興味あり stage gives the main roles and core creators equal shares, the ensemble and other staff less', () => {
  const s = {cast_text: '主役一、脇役二\nアンサンブル：' + Array.from({length: 30}, (_, i) => `群${i}`).join('、'),
    people: [['出演', '主役一'], ['出演', '脇役二'], ...Array.from({length: 30}, (_, i) => ['出演', `群${i}`]),
      ['演出', '演出家'], ['照明', '照明家']]};
  const m = interestShares(s, new Map());
  close(sum(m), 1);
  close(m.get(K('出演', '脇役二')), m.get(K('出演', '主役一')));
  close(m.get(K('出演', '群29')) / m.get(K('出演', '主役一')), LESSER_IMPORTANCE);
  close(m.get(K('演出', '演出家')), m.get(K('出演', '主役一')));
  close(m.get(K('照明', '照明家')) / m.get(K('演出', '演出家')), LESSER_IMPORTANCE);
});
