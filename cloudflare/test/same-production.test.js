// 同じ公演が 2 枚出ないよう、同じ題名の束をまとめる（recommend.sameProduction）。
// 起案者の指摘 2026-10-18「同じ公演が重複して2個あるときがある」「ラブ演劇博が2回出る」
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {sameProduction} from '../src/screens/recommend.js';

// stage_id -> [tkey, gkey, 劇場, 作り手の名前]
const rows = {
  '1': ['ぶたい', 'げきだん', '劇場A', ['俳優甲']],
  '2': ['べつ', 'げきだん', '劇場A', ['俳優甲']],
  '3': ['ぶたい', 'げきだん', '劇場B', []],          // 団体が同じ → 1 と同じ公演
  '4': ['ぶたい', '', '劇場C', []],                  // 団体が無い → 1 と同じ公演
  '5': ['ぶたい', 'ほか', '劇場A', []],              // 団体は違うが劇場が同じ → 1 と同じ公演
  '6': ['ぶたい', 'ほか', '劇場D', ['俳優甲']],      // 劇場も違うが同じ人がいる → 1 と同じ公演
  '7': ['ぶたい', 'ほか', '劇場E', ['俳優乙']],      // 団体・劇場・人のどれも違う → 別の公演（同じ題名の別の上演）
};
const db = {prepare: () => ({bind: (_ver, ...ids) => ({all: async () => ({results: ids.map(id => ({
  stage_id: id, tkey: rows[id][0], gkey: rows[id][1], th: rows[id][2],
  credits: JSON.stringify(rows[id][3].map(n => ['出演', n])),
}))})})})};

test('same title is one card when group, venue or a person matches; otherwise two', async () => {
  const groups = Object.keys(rows).map(id => ({stage_id: id, tour: 'T' + id}));
  const out = await sameProduction(db, 'v', groups);
  assert.deepEqual(out.map(g => g.stage_id), ['1', '2', '7']);
  assert.deepEqual(out[0].aliases, ['T3', 'T4', 'T5', 'T6']);
});

test('a merged stage without a tour key is kept as an extra venue', async () => {
  const out = await sameProduction(db, 'v', [{stage_id: '1', tour: 'T1'}, {stage_id: '3', tour: ''}]);
  assert.deepEqual(out.map(g => g.stage_id), ['1']);
  assert.deepEqual(out[0].aliasStages, ['3']);
});

test('a production answered under another stage id stays out', async () => {
  // 1 に答えた。3（団体が同じ）と 7（別の上演）が候補
  const out = await sameProduction(db, 'v', [{stage_id: '3', tour: 'T3'}, {stage_id: '7', tour: 'T7'}], undefined, ['1']);
  assert.deepEqual(out.map(g => g.stage_id), ['7']);
});
