// 所属（劇団）から推し量る（起案者の指示 2026-10-19「その進め方で進めてみて」、dec-affil-reco）。
import {DatabaseSync} from 'node:sqlite';
import {readFileSync, readdirSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {troupeValues, withAffil, affilSince, scoreFromIndex, d1Access, AFFIL_W, AFFIL_SMALL} from '../src/recommend.js';
import {chooseVariant} from '../src/reco-gate.js';

const K = p => '出演\u0000' + p;
const close = (a, b) => assert.ok(Math.abs(a - b) < 1e-9, `${a} != ${b}`);

test('an unseen member gets a share of the troupe value; members with their own value keep it', () => {
  const values = new Map([[K('甲'), [2, 0.6]], [K('乙'), [1, 0.3]]]);
  const members = new Map([['劇団X', ['甲', '乙', '丙']]]);
  const tv = troupeValues(values, members);
  close(tv.get('劇団X')[1], (0.6 + 0.3) / (2 + 3));
  const {values: out, via} = withAffil(values, members);
  assert.deepEqual(out.get(K('甲')), [2, 0.6]);
  close(out.get(K('丙'))[1], AFFIL_W * tv.get('劇団X')[1]);
  assert.equal(out.get(K('丙'))[0], 0);
  assert.deepEqual([...via], [[K('丙'), '劇団X']]);
  assert.equal(values.has(K('丙')), false, 'the input is not changed');
});

test('a big troupe gives each member less; a favourite troupe counts without any rated member', () => {
  const values = new Map([[K('甲'), [1, 0.5]]]);
  const big = Array.from({length: 40}, (_, i) => `員${i}`);
  const small = withAffil(values, new Map([['小', ['甲', '乙']]])).values.get(K('乙'))[1];
  const large = withAffil(values, new Map([['大', ['甲', ...big]]])).values.get(K('員1'))[1];
  close(large, small * Math.sqrt(AFFIL_SMALL / 41));
  const fav = withAffil(new Map(), new Map([['好き', ['丁']]]), new Set(['好き'])).values.get(K('丁'));
  assert.ok(fav[1] > 0);
  assert.equal(withAffil(new Map(), new Map([['ほか', ['丁']]])).values.size, 0);
});

test('the last three years only', () => {
  assert.equal(affilSince('2026-10-19'), '2023-10-19');
  assert.equal(affilSince(''), '');
});

test('the gate measures the affiliation variant but never chooses it', () => {
  // Every rated stage shares a troupe; the members liked in earlier blocks predict the later ones.
  const rated = [];
  for (let i = 0; i < 40; i++) {
    const good = i % 2 === 0;
    rated.push({key: `w${i}`, stage_id: `s${i}`, verdict: good ? '◎' : '×', rated_at: `2026-01-${String(i + 1).padStart(2, '0')}`,
      people: [['出演', good ? `良${i}` : `悪${i}`]]});
  }
  const members = new Map([['良劇団', Array.from({length: 40}, (_, i) => `良${i}`)], ['悪劇団', Array.from({length: 40}, (_, i) => `悪${i}`)]]);
  const got = chooseVariant(rated, {affil: members});
  assert.ok(got.checked.affil, 'measured');
  assert.ok(got.checked.affil.wins > got.checked.affil.losses, JSON.stringify(got.checked.affil));
  assert.notEqual(got.variant, 'affil');
  assert.equal(chooseVariant(rated).checked.affil, undefined, 'not measured without the tree');
});

test('scoreFromIndex: a member of a liked troupe raises a coming stage, with the troupe as the reason', async () => {
  const sqlite = new DatabaseSync(':memory:');
  for (const f of readdirSync(new URL('../migrations/', import.meta.url)).filter(n => n.endsWith('.sql')).sort()) sqlite.exec(readFileSync(new URL(`../migrations/${f}`, import.meta.url), 'utf8'));
  const db = {prepare: sql => { const st = sqlite.prepare(sql); return {bind: (...a) => ({all: async () => ({results: st.all(...a)}), first: async () => st.get(...a), raw: async () => st.all(...a).map(r => Object.values(r))})}; }};
  sqlite.exec(`INSERT INTO rec_stage(ver,stage_id,title,start,end) VALUES('v','10','客演の舞台','2026-12-01','2026-12-03');
    INSERT INTO rec_credit(ver,role,person,stage_id,role_w,role_group) VALUES('v','出演','丙','10',1.0,'cast');
    INSERT INTO rec_affil(ver,affil,person,stage_id,start,kind,written) VALUES
      ('v','劇団X','甲','1','2025-01-01','劇団','劇団X'),('v','劇団X','丙','2','2025-06-01','劇団','劇団X'),
      ('v','劇団X','古','3','2019-01-01','劇団','劇団X'),('v','事務所Y','甲','1','2025-01-01','事務所','事務所Y');`);
  const access = d1Access(db, 'v');
  const members = await access.affilMembers(['甲'], [], affilSince('2026-10-19'));
  assert.deepEqual([...members], [['劇団X', ['丙', '甲']]], 'troupes only, the last three years only');
  const rated = [{key: 'a', stage_id: '1', verdict: '◎', rated_at: '2026-01-01', people: [['出演', '甲']]},
    {key: 'b', stage_id: '5', verdict: '×', rated_at: '2026-01-02', people: [['出演', '丁']]}];
  const without = await scoreFromIndex({...access, rated, today: '2026-10-19'});
  assert.equal(without.length, 0);
  const got = await scoreFromIndex({...access, rated, today: '2026-10-19', affil: {members}});
  assert.deepEqual(got.map(c => [c.stage_id, c.affil]), [['10', [['出演\t丙', '劇団X']]]]);
  const off = await scoreFromIndex({...access, rated, today: '2026-10-19', affil: {members}, ablate: {affil: true}});
  assert.equal(off.length, 0);
});
