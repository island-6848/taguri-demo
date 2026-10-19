// 同じ人ばかり出るのを和らげる（起案者の指示 2026-10-15）: 並べ直し（spreadLeads）と 1 段広げる（scoreFromIndex の expand）。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {scoreFromIndex, EXPAND_WEIGHT} from '../src/recommend.js';
import {spreadLeads} from '../src/screens/recommend.js';

const g = (id, person) => ({stage_id: id, parts: person ? [[1, '出演', person, 1]] : [], kinds: []});

test('a page shows at most two shows led by the same person; the rest move down, none is dropped', () => {
  const groups = [g('a1', 'A'), g('a2', 'A'), g('a3', 'A'), g('a4', 'A'), g('b1', 'B'), g('k1', ''), g('c1', 'C')];
  const out = spreadLeads(groups, 4, 2).map(x => x.stage_id);
  assert.deepEqual(out.slice(0, 4), ['a1', 'a2', 'b1', 'k1']);
  assert.deepEqual(out.slice(4), ['a3', 'a4', 'c1']);
  assert.equal(out.length, groups.length);
  // Only one person left: the order is kept.
  assert.deepEqual(spreadLeads([g('a1', 'A'), g('a2', 'A'), g('a3', 'A')], 2, 1).map(x => x.stage_id), ['a1', 'a2', 'a3']);
});

const CREDITS = [['出演', 'P', 'S2', 1, 'cast'], ['出演', 'Q', 'S2', 1, 'cast'], ['出演', 'Q', 'S3', 1, 'cast'], ['出演', 'X', 'S3', 1, 'cast']];
const access = {
  postingsFor: async keys => { const want = new Set(keys.map(k => k.join('\u0000'))); return CREDITS.filter(c => want.has(c[0] + '\u0000' + c[1])); },
  stagesFor: async ids => new Map(ids.map(id => [id, {start: '2026-12-01', end: '2026-12-10', tour: ''}])),
};
const rated = [{key: 'r1', verdict: '◎', people: [['出演', 'P']], updated_at: '1'}, {key: 'r2', verdict: '×', people: [['出演', 'Z']], updated_at: '2'}];
const peopleFor = async ids => new Map(ids.filter(id => id === 'S2').map(id => [id, [['出演', 'P'], ['出演', 'Q']]]));

test('one step out: a show of someone who works with a liked person comes in, with the reason', async () => {
  const plain = await scoreFromIndex({...access, rated, today: '2026-10-15'});
  assert.deepEqual(plain.map(c => c.stage_id), ['S2']);
  const wide = await scoreFromIndex({...access, rated, today: '2026-10-15', expand: {peopleFor}});
  assert.deepEqual(wide.map(c => c.stage_id), ['S2', 'S3']);
  const s3 = wide.find(c => c.stage_id === 'S3');
  assert.deepEqual(s3.via, [['出演\tQ', 'P']]);
  const s2 = wide.find(c => c.stage_id === 'S2');
  assert.ok(Math.abs(s3.b / s2.b - EXPAND_WEIGHT) < 1e-3, `${s3.b} vs ${s2.b}`);
  // The liked person's own show is not raised again by the partner.
  assert.equal(s2.b, plain[0].b);
  // Someone the user said was not on stage that night is not brought back.
  const off = await scoreFromIndex({...access, rated, today: '2026-10-15', expand: {peopleFor, exclude: new Set(['出演\u0000Q'])}});
  assert.deepEqual(off.map(c => c.stage_id), ['S2']);
});

test('the reason names the liked person the partner works with', async () => {
  const {reasonRows} = await import('../src/screens/recommend.js');
  const html = reasonRows({parts: [[0.1, '出演', 'Q', 0]], kinds: [], via: [['出演\tQ', 'P']]}, new Map());
  assert.match(html, /出演 <a class="rsl"[^>]*><b>Q<\/b><\/a><span class="n">（好きなPと同じ公演に関わる人）<\/span>/);
});

// 起案者の指摘 2026-10-16「おすすめ理由に料金出たまま」: 本番の索引に残っている料金帯（#値段）の行は読まない。
test('a price band left in the index raises nothing and is no reason', async () => {
  const withPrice = [...CREDITS, ['#値段', '〜5000円', 'S2', 1, 'price'], ['#値段', '〜5000円', 'S4', 1, 'price']];
  const acc = {...access, postingsFor: async keys => { const want = new Set(keys.map(k => k.join('\u0000'))); return withPrice.filter(c => want.has(c[0] + '\u0000' + c[1])); }};
  const r = [...rated, {key: 'r3', verdict: '◎', people: [['#値段', '〜5000円']], updated_at: '3'}];
  const out = await scoreFromIndex({...acc, rated: r, today: '2026-10-15'});
  assert.deepEqual(out.map(c => c.stage_id), ['S2']);
  assert.ok(out.every(c => c.kinds.every(k => k[1] !== '#値段')));
});
