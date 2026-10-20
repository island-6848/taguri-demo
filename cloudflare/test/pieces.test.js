// 1 回の観劇で複数の作品を観た記録を、作品ごとに分けて評価する（起案者の指示 2026-10-19、dec-split-pieces）。
// 人の値には、その人が出た作品の評価の平均を、出た作品の数 m を m / (1 + (m − 1)·0.4) に縮めた重みで 1 回だけ足す。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {personValues, independentRatings, pieceWeight, PIECE_RHO, ratingCount, CONF_K} from '../src/recommend.js';

const Z = Math.sqrt(12) / 4;            // ◎ と × が 1 件ずつのときの ◎ の z（× は −Z）
const near = (a, b) => assert.ok(Math.abs(a - b) < 1e-9, `${a} ≠ ${b}`);
const value = (vals, person) => vals.get('出演\u0000' + person)[1];
const other = {key: 'x', stage_id: 'S0', verdict: '×', people: [['出演', '別の人']], rated_at: '1'};
// 10 本のオムニバス。亀田さんは全作品、ほかの俳優は 1 本ずつ
const pieces = (verdicts, occasion = 'o') => verdicts.map((v, i) => ({key: `${occasion}\u0000${i}`, occasion, share: 1 / verdicts.length,
  stage_id: 'S1', verdict: v, rated_at: '2', people: [['出演', '亀田'], ['出演', `俳優${i}`]]}));

test('ρ is the decided 0.4: 10 pieces count as 2.17 ratings, and never more than 2.5', () => {
  assert.equal(PIECE_RHO, 0.4);
  assert.equal(pieceWeight(1), 1);
  near(pieceWeight(6), 6 / 3);
  near(pieceWeight(10), 10 / 4.6);
  assert.ok(pieceWeight(1000) < 1 / PIECE_RHO);
});

test('someone in all 10 pieces rated ◎ rises a little, not tenfold', () => {
  const split = personValues(independentRatings([other, ...pieces(Array(10).fill('◎'))]));
  const whole = personValues([other, {key: 'o', stage_id: 'S1', verdict: '◎', rated_at: '2', people: [['出演', '亀田'], ['出演', '俳優0']]}]);
  near(value(whole, '亀田'), Z / (1 + CONF_K));
  near(value(split, '亀田'), Z * pieceWeight(10) / (pieceWeight(10) + CONF_K));
  assert.ok(value(split, '亀田') < 10 * Z / (10 + CONF_K));      // 1 本ずつ満額で数えたときより小さい
  // 1 本だけに出た人は、その作品の評価を 1 件ぶん
  near(value(split, '俳優3'), Z / (1 + CONF_K));
  // 1 回の観劇は 1 件（数は種の薄まりにも使う）
  assert.equal(split.get('出演\u0000亀田')[0], 1);
  near(ratingCount([other, ...pieces(Array(10).fill('◎'))]), 2);
});

test('the pieces\' ratings average for the shared people and reach the ones only in each piece', () => {
  const rows = [other, ...pieces(['◎', '×'])];
  const vals = personValues(independentRatings(rows));
  // 順位の分母: × の記録 1 件 + 観劇 1 件（◎ と × が半分ずつ）= 2 件。◎ は下に 1.5 件、同じが 0.5 件
  const zTop = ((1.5 + 0.25) / 2 - 0.5) * Math.sqrt(12), zLow = ((0 + 0.5 * 1.5) / 2 - 0.5) * Math.sqrt(12);
  near(value(vals, '亀田'), ((zTop + zLow) / 2) * pieceWeight(2) / (pieceWeight(2) + CONF_K));
  near(value(vals, '俳優0'), zTop / (1 + CONF_K));
  near(value(vals, '俳優1'), zLow / (1 + CONF_K));
});

test('a later visit to the same stage replaces an earlier one, pieces and all', () => {
  const first = pieces(['◎', '◎'], 'early').map(r => ({...r, rated_at: '1'}));
  const later = pieces(['×', '◎', '◎'], 'late').map(r => ({...r, rated_at: '3'}));
  const kept = independentRatings([...first, ...later]);
  assert.deepEqual(kept.map(r => r.key), later.map(r => r.key));
});

// 朗読劇とほかの形式を兼ねる公演（dec-reading-dual-form）: 朗読劇 6・ほかの形式 4 で数える（起案者 2026-10-20）
test('a reading that is also a musical play counts 朗読劇 six and 音楽劇 four', async () => {
  const {kindShares, READING_SHARE} = await import('../src/recommend.js');
  const R = '#形式\u0000朗読劇', M = '#形式\u0000音楽劇';
  assert.equal(READING_SHARE, 0.6);
  assert.deepEqual([...kindShares([R, M, '出演\u0000甲'])], [[R, 0.6], [M, 0.4]]);
  assert.equal(kindShares([R, '出演\u0000甲']).size, 0);                 // 朗読劇だけ: 1
  assert.equal(kindShares(['#形式\u0000ミュージカル', M]).size, 0);      // 朗読劇の無い 2 つ: 1 のまま
  const people = [['出演', '甲'], ['#形式', '朗読劇'], ['#形式', '音楽劇']];
  const vals = personValues([other, {key: 'j', stage_id: 'S9', verdict: '◎', rated_at: '2', people}]);
  near(vals.get(R)[1], Z * 0.6 / (0.6 + CONF_K));
  near(vals.get(M)[1], Z * 0.4 / (0.4 + CONF_K));
  near(vals.get('出演\u0000甲')[1], Z / (1 + CONF_K));
});
