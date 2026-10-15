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

test('(3) what is also in 興味なし weighs less; what is only in 興味あり more', () => {
  const liked = [{people: [['出演', 'どちらも'], ['出演', 'ありだけ']]}];
  const disliked = [{people: [['出演', 'どちらも'], ['出演', 'なしだけ']]}];
  const c = interestContrast(liked, disliked);
  assert.deepEqual(c.get(K('出演', 'どちらも')), [1, 1]);
  const m = interestShares(liked[0], new Map(), c);
  close(m.get(K('出演', 'ありだけ')), 2 / 3);
  close(m.get(K('出演', 'どちらも')), 1 / 3);
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
