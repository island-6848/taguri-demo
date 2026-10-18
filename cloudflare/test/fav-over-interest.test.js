// 推薦の強さは お気に入り ＞ 興味あり（起案者の指示 2026-10-18）。recommend.personValues の FAV_SEED_W
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {personValues} from '../src/recommend.js';

test('a person reached through a favourite counts more than one reached through 興味あり', () => {
  // どちらも 1 公演ずつ、同じ形（出演者 2 人）。種（お気に入りの公演）にいる甲と、興味ありの公演にいる乙を比べる
  const seed = {stage_id: 's', people: [['出演', '甲'], ['出演', '丙']]};
  const liked = {stage_id: 'l', people: [['出演', '乙'], ['出演', '丁']]};
  const v = personValues([], [seed], new Set(), [liked], []);
  const val = k => (v.get(k) || [0, 0])[1];
  assert.ok(val('出演\u0000甲') > val('出演\u0000乙'), `${val('出演\u0000甲')} > ${val('出演\u0000乙')}`);
});
