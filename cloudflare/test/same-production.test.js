// 同じ公演が 2 枚出ないよう、題名（tkey）と団体（gkey）が同じ束をまとめる（recommend.sameProduction）。
// 起案者の指摘 2026-10-18「同じ公演が重複して2個あるときがある」
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {sameProduction} from '../src/screens/recommend.js';

const keys = {'1': ['ぶたい', 'げきだん'], '2': ['べつ', 'げきだん'], '3': ['ぶたい', 'げきだん'], '4': ['ぶたい', 'ほか']};
const db = {prepare: () => ({bind: (_ver, ...ids) => ({all: async () => ({results: ids.map(id => ({stage_id: id, tkey: keys[id][0], gkey: keys[id][1]}))})})})};

test('a later group with the same title and group is folded into the first, keeping its venues', async () => {
  const groups = [{stage_id: '1', tour: 'A'}, {stage_id: '2', tour: 'B'}, {stage_id: '3', tour: 'C'}, {stage_id: '4', tour: 'D'}];
  const out = await sameProduction(db, 'v', groups);
  assert.deepEqual(out.map(g => g.stage_id), ['1', '2', '4']);
  assert.deepEqual(out[0].aliases, ['C']);
});
